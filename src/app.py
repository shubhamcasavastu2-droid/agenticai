"""
Application Layer for Agentic CLI.

This module provides the Application class that orchestrates the entire system:
- Initializes all components (provider, CLI, tools, permissions, processors)
- Registers built-in tools (read_file, write_file, edit_file, glob, grep, bash, ask_user, plan, todo)
- Loads skills and agents from the capabilities system (root_dir + workspace_dir)
- Builds the system prompt with tool descriptions and tagged skills/agents
- Runs the main agent loop with completion review
- Routes slash commands to appropriate processors
- All process channels share the same session

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
from .core.session import SessionStore
from .logger import (
    log_error,
    log_exception,
    log_info,
)
from .models import SessionModel, TaskStatus
from .prompt import (
    build_agents_section,
    build_skills_section,
    get_command_allowed_tools,
    get_command_summary,
    get_processor_class,
    get_tool_descriptions,
)
from .provider import (
    OpenAICompatibleProvider,
    ProviderAuthenticationError,
    ProviderTimeoutError,
)
from .processor import (
    PROCESSOR_CLASSES,
    BaseProcessor,
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
    CLI is responsible only for terminal/UI concerns (input, permissions, display).

    All process channels share the same session. Session can be created/switched
    via the /session command.
    """

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
            config.root_dir
            if isinstance(config.root_dir, Path)
            else Path(config.root_dir)
        )
        self.workspace_dir = (
            config.workspace_dir
            if isinstance(config.workspace_dir, Path)
            else Path(config.workspace_dir)
        )
        self.permission_gate = PermissionGate(
            config.workspace_dir, default_auto_allow=READ_ONLY_TOOLS
        )
        self.project_dir = self.workspace_dir
        self.agent_loop: AgentLoop | None = None
        self.completion_resolver: CompletionResolver | None = None
        self.skill_loader: SkillLoader | None = None
        self.agent_loader: AgentLoader | None = None
        self.session: SessionModel | None = None
        self.session_store: SessionStore | None = None
        self.processors: dict[str, BaseProcessor] = {}
        self._ui = Display(console=self.cli.console)

    # ------------------------------------------------------------------ provider setup

    def _make_provider(self, model: str, stream: bool) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            base_url=self.config.model.base_url,
            api_key=self.config.model.api_key,
            model=model,
            timeout=self.config.model.request_timeout_seconds,
            max_completion_tokens=self.config.model.max_completion_tokens,
            max_retries=self.config.model.max_retries,
            stream=stream,
            on_text_delta=self.cli.on_text_delta if stream else None,
        )

    async def build_providers(self) -> None:
        self.providers["agent"] = self._make_provider(self.config.model.model, self.config.model.stream)
        self.providers["planner"] = self._make_provider(self.config.model.model, False)
        self.providers["ask"] = self._make_provider(
            self.config.model.review_model or self.config.model.model, False
        )
        self.providers["optimization"] = self._make_provider(
            self.config.model.review_model or self.config.model.model, False
        )
        self.provider = self.providers["agent"]
        self.review_provider = self.providers["ask"]

    async def close(self) -> None:
        for provider in (self.provider, self.review_provider):
            if provider:
                await provider.close()

    # ------------------------------------------------------------------ initialization

    async def initialize(self) -> None:
        await self.build_providers()
        assert self.provider is not None

        # Initialize session
        self.session_store = SessionStore(self.config.sessions_path)
        self.session = SessionModel(
            session_id="default",
            workspace_dir=str(self.workspace_dir),
            root_dir=str(self.root_dir),
        )

        # Register file tools with the workspace root
        max_output = self.config.model.max_output_size
        self.registry.register(create_read_file_tool(self.workspace_dir, max_output))
        self.registry.register(create_write_file_tool(self.workspace_dir))
        self.registry.register(create_edit_file_tool(self.workspace_dir))
        self.registry.register(create_glob_tool(self.workspace_dir, max_output))
        self.registry.register(create_grep_tool(self.workspace_dir, max_output))
        self.registry.register(create_bash_tool(self.workspace_dir, max_output))
        self.registry.register(create_ask_user_tool(self.cli.ask_user))
        self.registry.register(create_plan_tool(self.cli.present_plan))
        self.registry.register(create_todo_tool(self.cli._todo_callback))
        self.registry.register(create_change_workspace_tool(self.refresh_workspace))

        # Load skills and agents from both root_dir and workspace_dir
        self._load_skills_agents()

        # Build system prompt for default command
        system_prompt = self._build_system_prompt("agents-default")
        self.agent_loop = AgentLoop(
            provider=self.provider,
            providers=self.providers,
            registry=self.registry,
            permission_gate=self.permission_gate,
            system_prompt=system_prompt,
            max_steps=self.config.model.max_steps,
            permission_callback=self.cli._permission_callback,
            reasoning_callback=self.cli._reasoning_callback,
            tool_callback=self.cli._tool_callback,
            clarification_callback=self.cli._clarify_empty_response,
            continuation_callback=self.cli._ask_continue,
            context_window_tokens=self.config.model.context_window_tokens,
            max_completion_tokens=self.config.model.max_completion_tokens,
        )

        # Initialize all processors
        self._init_processors()

        # Wire initialized components into CLI
        self.cli.provider = self.provider
        self.cli.providers = self.providers
        self.cli.review_provider = self.review_provider
        self.cli.registry = self.registry
        self.cli.agent_loop = self.agent_loop
        self.cli.completion_resolver = self.completion_resolver
        self.cli.skill_loader = self.skill_loader
        self.cli.agent_loader = self.agent_loader
        self.cli.session = self.session

    def _load_skills_agents(self) -> None:
        """Load skills and agents from both root_dir and workspace_dir."""
        root_skills_dir = self.root_dir / ".agents" / "skills"
        root_agents_dir = self.root_dir / ".agents" / "agents"
        root_agents_md = self.root_dir / ".agents" / "agents.md"

        self.skill_loader = SkillLoader(root_skills_dir)
        self.skill_loader.discover()

        self.agent_loader = AgentLoader(root_agents_dir, root_agents_md)
        self.agent_loader.discover()

        # Workspace skills/agents take priority
        workspace_skills_dir = self.workspace_dir / ".agents" / "skills"
        if workspace_skills_dir.exists():
            ws_skill_loader = SkillLoader(workspace_skills_dir)
            ws_skill_loader.discover()
            for skill in ws_skill_loader.all():
                self.skill_loader._skills[skill.name] = skill

        workspace_agents_dir = self.workspace_dir / ".agents" / "agents"
        workspace_agents_md = self.workspace_dir / ".agents" / "agents.md"
        if workspace_agents_dir.exists() or workspace_agents_md.exists():
            ws_agent_loader = AgentLoader(workspace_agents_dir, workspace_agents_md)
            ws_agent_loader.discover()
            for agent in ws_agent_loader.all():
                self.agent_loader._agents[agent.name] = agent

    def _init_processors(self) -> None:
        """Initialize all slash command processors."""
        for cmd_name, processor_class in PROCESSOR_CLASSES.items():
            processor = processor_class(
                command=cmd_name,
                config=self.config,
                provider=self.provider,
                registry=self.registry,
                session=self.session,
            )
            self.processors[cmd_name] = processor

    def _build_system_prompt(self, command: str) -> str:
        """Build the system prompt for a given command."""
        return build_system_prompt(
            command=command,
            tool_descriptions=get_tool_descriptions(self.registry.all()),
            working_dir=str(self.workspace_dir),
        )

    def _refresh_skills_agents(self) -> None:
        """Refresh skills and agents from both root_dir and workspace_dir."""
        self._load_skills_agents()

    async def refresh_workspace(self, new_workspace_dir: str | Path) -> None:
        """Re-initialize workspace-dependent components after a workspace change.

        Only workspace_dir changes; root_dir stays constant.
        """
        new_dir = Path(new_workspace_dir).expanduser().resolve()

        if not new_dir.is_dir():
            raise ValueError(f"'{new_dir}' is not a valid directory")

        Project.set_workspace_dir(new_dir)
        self.config.workspace_dir = new_dir
        self.workspace_dir = new_dir
        self.project_dir = new_dir

        root = self.root_dir
        workspace = new_dir
        max_output = self.config.model.max_output_size

        # Re-register file tools with the new workspace root
        self.registry.register(create_read_file_tool(workspace, max_output))
        self.registry.register(create_write_file_tool(workspace))
        self.registry.register(create_edit_file_tool(workspace))
        self.registry.register(create_glob_tool(workspace, max_output))
        self.registry.register(create_grep_tool(workspace, max_output))
        self.registry.register(create_bash_tool(workspace, max_output))

        # Re-load skills/agents
        self._load_skills_agents()

        # Rebuild system prompt
        system_prompt = self._build_system_prompt("agents-default")
        if self.agent_loop:
            self.agent_loop.system_prompt = system_prompt

        # Update CLI references
        self.cli.registry = self.registry
        self.cli.skill_loader = self.skill_loader
        self.cli.agent_loader = self.agent_loader

        self._ui.console.print(
            f"[status.success]Workspace changed to:[/status.success] {new_dir}"
        )

    async def refresh_agents_skills_on_input(self) -> None:
        """Refresh skills and agents from .agents folders on every user input."""
        self._load_skills_agents()

        workspace = self.workspace_dir
        system_prompt = self._build_system_prompt("agents-default")
        if self.agent_loop:
            self.agent_loop.system_prompt = system_prompt

        self.cli.registry = self.registry
        self.cli.skill_loader = self.skill_loader
        self.cli.agent_loader = self.agent_loader

    def get_processor(self, command: str) -> BaseProcessor | None:
        """Get the processor for a given slash command."""
        return self.processors.get(command)

    def get_or_create_processor(self, command: str) -> BaseProcessor | None:
        """Get or create a processor for a given command."""
        if command not in self.processors:
            processor_class = PROCESSOR_CLASSES.get(command)
            if processor_class is None:
                return None
            processor = processor_class(
                command=command,
                config=self.config,
                provider=self.provider,
                registry=self.registry,
                session=self.session,
            )
            self.processors[command] = processor
        return self.processors[command]

    # ------------------------------------------------------------------ run

    async def run(self) -> None:
        """Main application loop.

        On every user input:
        1. Refreshes .agents folders and rebuilds system prompt
        2. If input starts with '/', route to the appropriate slash command processor
        3. Otherwise, process as normal agent input
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

                # Check if this is a slash command
                if user_input.startswith("/"):
                    await self._handle_slash_command(user_input)
                else:
                    await self._process_normal_input(user_input)

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
                    f"{self.config.model.request_timeout_seconds}s)."
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

    async def _handle_slash_command(self, user_input: str) -> None:
        """Handle a slash command input.

        Parses the command and routes to the appropriate processor.
        """
        parts = user_input.split()
        cmd_name = parts[0].lstrip("/")
        cmd_args = parts[1:] if len(parts) > 1 else []

        processor = self.get_or_create_processor(cmd_name)
        if processor is None:
            self._ui.console.print(
                f"[status.error]Unknown command:[/status.error] /{cmd_name}"
            )
            self._ui.console.print("Available commands: " + ", ".join(get_processor_summary()))
            return

        # Process through the command processor
        try:
            result = await processor.process(user_input)
            self.cli.end_stream()
            self._ui.agent_response(result)
        except Exception as e:
            self.cli.end_stream()
            self._ui.error(f"Command error ({type(e).__name__}): {e}")
            log_exception(e)

    async def _process_normal_input(self, user_input: str) -> None:
        """Process normal (non-slash-command) user input through the agent loop."""
        assert self.completion_resolver is not None
        normalized_input = await self.completion_resolver.normalize_input(user_input)
        if normalized_input.startswith("Error:"):
            self.cli.end_stream()
            self._ui.normalization_failed(normalized_input)
            return
        self.cli._create_todos_from_normalized(normalized_input)

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
