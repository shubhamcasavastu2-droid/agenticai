"""
Application Layer for Agentic CLI.

This module provides the Application class that orchestrates the entire system:
- Initializes all components (provider, CLI, tools, permissions, completion resolver)
- Registers built-in tools (read_file, write_file, edit_file, glob, grep, bash, ask_user, plan, todo)
- Loads skills and agents from the capabilities system (root_dir + workspace_dir)
- Builds the system prompt with tool descriptions and tagged skills/agents
- Runs the main agent loop with completion review
- On every user input, refreshes .agents folders and rebuilds system prompt

The Application separates initialization concerns from the CLI's terminal/UI concerns.
"""

from __future__ import annotations

from pathlib import Path

from .capabilities.agents import AgentLoader
from .capabilities.skills import SkillLoader
from .cli import CLI
from .config.config import Config
from .config.project_dir import Project
from .core.agent import AgentLoop
from .core.completion import CompletionResolver
from .logger import (
    log_error,
    log_exception,
)
from .prompt.system_prompt import (
    AgentInfo,
    SkillInfo,
    build_agents_section,
    build_skills_section,
    build_system_prompt,
    get_tool_descriptions,
)
from .provider import (
    OpenAICompatibleProvider,
    ProviderAuthenticationError,
    ProviderTimeoutError,
)
from .security.permissions import READ_ONLY_TOOLS, PermissionGate
from .tools import (
    ToolRegistry,
    create_ask_user_tool,
    create_bash_tool,
    create_change_workspace_tool,
    create_edit_file_tool,
    create_glob_tool,
    create_grep_tool,
    create_plan_tool,
    create_read_file_tool,
    create_todo_tool,
    create_write_file_tool,
)
from .ui import Display


class Application:
    """Application layer: owns initialization and the agent loop execution.
    CLI is responsible only for terminal/UI concerns (input, permissions, display)."""

    def __init__(self, config: Config):
        self.config = config
        self.cli = CLI(config)
        self.cli.app = self  # Back-reference for slash commands to trigger refresh
        self.providers: dict[str, OpenAICompatibleProvider] = {}
        self.provider: OpenAICompatibleProvider | None = None
        self.review_provider: OpenAICompatibleProvider | None = None
        self.registry = ToolRegistry()
        # root_dir is fixed (from Project singleton), workspace_dir is changeable
        self.root_dir = (
            config.root_dir.get_products_dir()
            if hasattr(config.root_dir, "get_products_dir")
            else config.root_dir
        )
        self.workspace_dir = (
            config.workspace_dir
            if hasattr(config.workspace_dir, "get_products_dir")
            else config.workspace_dir
        )
        self.permission_gate = PermissionGate(
            config.workspace_dir, default_auto_allow=READ_ONLY_TOOLS
        )
        self.project_dir = self.workspace_dir
        self.agent_loop: AgentLoop | None = None
        self.completion_resolver: CompletionResolver | None = None
        self.skill_loader: SkillLoader | None = None
        self.agent_loader: AgentLoader | None = None
        self._ui = Display(console=self.cli.console)

    # ------------------------------------------------------------------ provider setup

    def _make_provider(self, model: str, stream: bool) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            model=model,
            timeout=self.config.request_timeout_seconds,
            max_completion_tokens=self.config.max_completion_tokens,
            max_retries=self.config.max_retries,
            stream=stream,
            on_text_delta=self.cli.on_text_delta if stream else None,
        )

    async def build_providers(self) -> None:
        self.providers["agent"] = self._make_provider(self.config.model, self.config.stream)
        self.providers["planner"] = self._make_provider(self.config.model, False)
        self.providers["ask"] = self._make_provider(
            self.config.review_model or self.config.model, False
        )
        self.providers["optimization"] = self._make_provider(
            self.config.review_model or self.config.model, False
        )

    async def rebuild_providers(self) -> None:
        """(Re)create the agent and review providers from the current config."""
        await self.close()
        await self.build_providers()
        self.provider = self._make_provider(self.config.model, self.config.stream)
        self.review_provider = self._make_provider(
            self.config.review_model or self.config.model, False
        )
        if self.completion_resolver:
            self.completion_resolver.provider = self.provider
            self.completion_resolver.review_provider = self.review_provider

    async def close(self) -> None:
        for provider in (self.provider, self.review_provider):
            if provider:
                await provider.close()

    # ------------------------------------------------------------------ initialization

    def _build_skills_info(
        self, skill_loader: SkillLoader, root_skills_dir: Path, workspace_skills_dir: Path
    ) -> list[SkillInfo]:
        """Build SkillInfo list with tagging: [EXISTING] for root, [NEW] for workspace."""
        skills: list[SkillInfo] = []

        # Root skills are [EXISTING]
        for skill in skill_loader.all():
            skills.append(
                SkillInfo(
                    name=skill.name,
                    description=skill.description or "",
                    path=str(skill.path),
                    source="root",
                    tag="[EXISTING]",
                )
            )

        # Workspace skills are [NEW] (or override root)
        if workspace_skills_dir.exists():
            ws_loader = SkillLoader(workspace_skills_dir)
            ws_loader.discover()
            for skill in ws_loader.all():
                skills.append(
                    SkillInfo(
                        name=skill.name,
                        description=skill.description or "",
                        path=str(skill.path),
                        source="workspace",
                        tag="[NEW]",
                    )
                )

        return skills

    def _build_agents_info(
        self, agent_loader: AgentLoader, root_agents_dir: Path, workspace_agents_dir: Path
    ) -> list[AgentInfo]:
        """Build AgentInfo list with tagging: [EXISTING] for root, [NEW] for workspace."""
        agents: list[AgentInfo] = []

        # Root agents are [EXISTING]
        for agent in agent_loader.all():
            agents.append(
                AgentInfo(
                    name=agent.name,
                    description=agent.description or "",
                    path=str(agent.path if hasattr(agent, "path") else ""),
                    source="root",
                    tag="[EXISTING]",
                )
            )

        # Workspace agents are [NEW]
        if workspace_agents_dir.exists():
            ws_loader = AgentLoader(workspace_agents_dir, None)
            ws_loader.discover()
            for agent in ws_loader.all():
                agents.append(
                    AgentInfo(
                        name=agent.name,
                        description=agent.description or "",
                        path=str(agent.path if hasattr(agent, "path") else ""),
                        source="workspace",
                        tag="[NEW]",
                    )
                )

        return agents

    def _refresh_skills_agents(self) -> tuple[list[SkillInfo], list[AgentInfo]]:
        """Refresh skills and agents from both root_dir and workspace_dir.

        Root dir is loaded first (existing), workspace dir second (new/override).
        Returns (skills_info, agents_info) lists with tagging.
        """
        root = (
            self.config.root_dir.get_products_dir()
            if hasattr(self.config.root_dir, "get_products_dir")
            else self.config.root_dir
        )
        workspace = (
            self.config.workspace_dir
            if hasattr(self.config.workspace_dir, "get_products_dir")
            else self.config.workspace_dir
        )

        # Load root skills/agents first
        root_skills_dir = root / ".agents" / "skills"
        root_agents_dir = root / ".agents" / "agents"
        root_agents_md = root / ".agents" / "agents.md"

        self.skill_loader = SkillLoader(root_skills_dir)
        self.skill_loader.discover()

        self.agent_loader = AgentLoader(root_agents_dir, root_agents_md)
        self.agent_loader.discover()

        # Then load workspace skills/agents (workspace takes priority / tagged as [NEW])
        workspace_skills_dir = workspace / ".agents" / "skills"
        workspace_agents_dir = workspace / ".agents" / "agents"
        workspace_agents_md = workspace / ".agents" / "agents.md"

        if workspace_skills_dir.exists():
            ws_skill_loader = SkillLoader(workspace_skills_dir)
            ws_skill_loader.discover()
            for skill in ws_skill_loader.all():
                self.skill_loader._skills[skill.name] = skill

        if workspace_agents_dir.exists() or workspace_agents_md.exists():
            ws_agent_loader = AgentLoader(workspace_agents_dir, workspace_agents_md)
            ws_agent_loader.discover()
            for agent in ws_agent_loader.all():
                self.agent_loader._agents[agent.name] = agent

        # Build tagged info lists
        skills_info = self._build_skills_info(
            self.skill_loader, root_skills_dir, workspace_skills_dir
        )
        agents_info = self._build_agents_info(
            self.agent_loader, root_agents_dir, workspace_agents_dir
        )

        return skills_info, agents_info

    async def initialize(self) -> None:
        await self.rebuild_providers()
        assert self.provider is not None
        self.completion_resolver = CompletionResolver(
            self.provider,
            max_attempts=self.config.max_completion_attempts,
            review_provider=self.review_provider,
            enabled=self.config.completion_review,
            completion_review_prompt=self.config.completion_review_prompt,
            cli=self.cli,
            config=self.config,
        )

        root = (
            self.config.root_dir.get_products_dir()
            if hasattr(self.config.root_dir, "get_products_dir")
            else self.config.root_dir
        )
        workspace = (
            self.config.workspace_dir
            if hasattr(self.config.workspace_dir, "get_products_dir")
            else self.config.workspace_dir
        )
        max_output = self.config.max_output_size
        self.registry.register(create_read_file_tool(workspace, max_output))
        self.registry.register(create_write_file_tool(workspace))
        self.registry.register(create_edit_file_tool(workspace))
        self.registry.register(create_glob_tool(workspace, max_output))
        self.registry.register(create_grep_tool(workspace, max_output))
        self.registry.register(create_bash_tool(workspace, max_output))
        self.registry.register(create_ask_user_tool(self.cli.ask_user))
        self.registry.register(create_plan_tool(self.cli.present_plan))
        self.registry.register(create_todo_tool(self.cli._todo_callback))
        self.registry.register(create_change_workspace_tool(self.refresh_workspace))

        # Refresh skills/agents from both root_dir and workspace_dir
        skills_info, agents_info = self._refresh_skills_agents()

        system_prompt = build_system_prompt(
            workspace,
            get_tool_descriptions(self.registry.all()),
            root / "AGENT.md",
            build_skills_section(skills_info),
            build_agents_section(agents_info),
            system_prompt_template=self.config.system_prompt_template,
        )
        self.agent_loop = AgentLoop(
            provider=self.provider,
            providers=self.providers,
            registry=self.registry,
            permission_gate=self.permission_gate,
            system_prompt=system_prompt,
            max_steps=self.config.max_steps,
            permission_callback=self.cli._permission_callback,
            reasoning_callback=self.cli._reasoning_callback,
            tool_callback=self.cli._tool_callback,
            clarification_callback=self.cli._clarify_empty_response,
            continuation_callback=self.cli._ask_continue,
            context_window_tokens=self.config.context_window_tokens,
            max_completion_tokens=self.config.max_completion_tokens,
        )

        # Wire initialized components into CLI
        self.cli.provider = self.provider
        self.cli.providers = self.providers
        self.cli.review_provider = self.review_provider
        self.cli.registry = self.registry
        self.cli.agent_loop = self.agent_loop
        self.cli.completion_resolver = self.completion_resolver
        self.cli.skill_loader = self.skill_loader
        self.cli.agent_loader = self.agent_loader

    async def refresh_workspace(self, new_workspace_dir: str | Path) -> None:
        """Re-initialize workspace-dependent components after a workspace change.

        Only workspace_dir changes; root_dir stays constant. Re-registers file tools
        with the new workspace, re-discovers skills/agents from both root and workspace
        (workspace takes priority), and rebuilds the system prompt.
        """
        from pathlib import Path

        new_dir = Path(new_workspace_dir).expanduser().resolve()

        if not new_dir.is_dir():
            raise ValueError(f"'{new_dir}' is not a valid directory")

        # Update the workspace_dir in Project singleton; root_dir stays constant
        Project.set_workspace_dir(new_dir)
        # Also update the config's workspace_dir
        self.config.workspace_dir = new_dir

        root = (
            self.config.root_dir.get_products_dir()
            if hasattr(self.config.root_dir, "get_products_dir")
            else self.config.root_dir
        )
        workspace = new_dir
        max_output = self.config.max_output_size

        # Re-register file tools with the new workspace root
        self.registry.register(create_read_file_tool(workspace, max_output))
        self.registry.register(create_write_file_tool(workspace))
        self.registry.register(create_edit_file_tool(workspace))
        self.registry.register(create_glob_tool(workspace, max_output))
        self.registry.register(create_grep_tool(workspace, max_output))
        self.registry.register(create_bash_tool(workspace, max_output))

        # Re-load skills from root_dir first, then workspace_dir (workspace takes priority)
        skills_info, agents_info = self._refresh_skills_agents()

        # Rebuild system prompt
        system_prompt = build_system_prompt(
            workspace,
            get_tool_descriptions(self.registry.all()),
            root / "AGENT.md",
            build_skills_section(skills_info),
            build_agents_section(agents_info),
            system_prompt_template=self.config.system_prompt_template,
        )
        self.agent_loop.system_prompt = system_prompt

        # Update CLI references
        self.cli.registry = self.registry
        self.cli.skill_loader = self.skill_loader
        self.cli.agent_loader = self.agent_loader

        self._ui.console.print(
            f"[status.success]Workspace changed to:[/status.success] {new_dir}"
        )

    async def refresh_agents_skills_on_input(self) -> None:
        """Refresh skills and agents from .agents folders on every user input.

        Re-discovers skills/agents from both root_dir and workspace_dir,
        rebuilds the system prompt with tagged info, and updates the agent loop.
        This ensures new skills/agents added to .agents folders are picked up
        immediately without restarting the CLI.
        """
        skills_info, agents_info = self._refresh_skills_agents()

        root = (
            self.config.root_dir.get_products_dir()
            if hasattr(self.config.root_dir, "get_products_dir")
            else self.config.root_dir
        )
        workspace = (
            self.config.workspace_dir
            if hasattr(self.config.workspace_dir, "get_products_dir")
            else self.config.workspace_dir
        )

        system_prompt = build_system_prompt(
            workspace,
            get_tool_descriptions(self.registry.all()),
            root / "AGENT.md",
            build_skills_section(skills_info),
            build_agents_section(agents_info),
            system_prompt_template=self.config.system_prompt_template,
        )
        if self.agent_loop:
            self.agent_loop.system_prompt = system_prompt

        # Update CLI references
        self.cli.registry = self.registry
        self.cli.skill_loader = self.skill_loader
        self.cli.agent_loader = self.agent_loader

    # ------------------------------------------------------------------ run

    async def run(self) -> None:
        """Main application loop: owns agent loop execution, delegates UI to CLI.

        On every user input, refreshes .agents folders and rebuilds the system
        prompt so newly added skills/agents are immediately available.
        """
        await self.initialize()
        while self.cli.running:
            try:
                user_input = await self.cli.prompt_user()
                if user_input is None:
                    continue
                if not self.agent_loop:
                    continue

                # Refresh skills/agents from .agents folders on every input
                await self.refresh_agents_skills_on_input()

                assert self.completion_resolver is not None
                normalized_input = await self.completion_resolver.normalize_input(user_input)
                if normalized_input.startswith("Error:"):
                    continue
                self.cli._create_todos_from_normalized(normalized_input)

                if self.completion_resolver is None:
                    raise RuntimeError("Completion resolver is not initialized")
                completion = await self.completion_resolver.run(
                    self.agent_loop,
                    original_request=user_input,
                    normalized_request=normalized_input,
                )
                self.cli.end_stream()

                if completion.complete:
                    self._ui.agent_response(completion.response)
                else:
                    status = (
                        f"Completion not verified after {completion.attempts} attempts. "
                        f"Remaining issue: {completion.findings or 'The reviewer could not confirm completion.'}"
                    )
                    self._ui.markdown_panel(
                        f"{completion.response}\n\n**{status}**",
                        title="Task not confirmed",
                        border_style="yellow",
                    )
            except (KeyboardInterrupt, EOFError):
                self.cli.end_stream()
                self.cli.console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
            except ProviderAuthenticationError as e:
                self.cli.end_stream()
                self._ui.error(f"Authentication error: {e}")
                log_error(str(e))
            except ProviderTimeoutError as e:
                self.cli.end_stream()
                self._ui.error(
                    "Model request timed out. "
                    "The model server did not respond within the configured timeout. "
                    "Check that the model server is running and responsive, or increase "
                    f"AGENTIC_REQUEST_TIMEOUT_SECONDS (current: "
                    f"{self.config.request_timeout_seconds}s)."
                )
                log_error(str(e))
            except Exception as e:
                self.cli.end_stream()
                detail = str(e).strip() or repr(e)
                self._ui.error(f"Error ({type(e).__name__}): {detail}")
                log_exception(e)
            finally:
                self.cli._save_session()
                self.cli._display_todos()
