"""
Slash command processors for Agentic CLI.

Each processor handles a specific slash command with its own system prompt,
tool restrictions, and workflow. All processors share the same session state.

Commands:
- /ask: Ask Processor - clarifying questions, read-only tools
- /plan: Planning Processor - create plans, save to docs/plans/*
- /agents-default: Agentic Processor - task breakdown, todo list
- /session: Session Processor - create/switch sessions
- /schedule: TODO placeholder
- /agent: Agent Creation Processor - create/update agents
- /skills: Skill Creation Processor - create/update skills
- /hook: TODO placeholder
- /orchestrator: TODO placeholder
- /job: Job Processor - create process channels
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..config.config import Config
from ..models import MessageModel, ProcessModel, SessionModel, TaskModel
from ..prompt import (
    build_system_prompt,
    get_command_allowed_tools,
    get_command_summary,
)
from ..provider import Provider
from ..tools import ToolRegistry


class BaseProcessor:
    """Base class for all slash command processors."""

    def __init__(
        self,
        command: str,
        config: Config,
        provider: Provider,
        registry: ToolRegistry,
        session: SessionModel | None = None,
    ):
        self.command = command
        self.config = config
        self.provider = provider
        self.registry = registry
        self.session = session
        self.process_model: ProcessModel | None = None
        self.allowed_tools = get_command_allowed_tools(command)

    def create_process(self, process_id: str) -> ProcessModel:
        """Create a process model for this command."""
        self.process_model = ProcessModel(
            process_id=process_id,
            command_type=self.command,
            session_id=self.session.session_id if self.session else "",
        )
        return self.process_model

    def get_system_prompt(self, working_dir: str = ".") -> str:
        """Build the system prompt for this command."""
        tool_descriptions = self._build_tool_descriptions()
        return build_system_prompt(
            command=self.command,
            tool_descriptions=tool_descriptions,
            working_dir=working_dir,
        )

    def _build_tool_descriptions(self) -> str:
        """Build tool description string for allowed tools."""
        lines = []
        for tool_name in self.allowed_tools:
            tool = self.registry.get(tool_name)
            if tool:
                lines.append(f"- **{tool.name}**: {tool.description}")
        return "\n".join(lines) if lines else "No tools available."

    def get_tools_for_command(self) -> list:
        """Get the tool instances allowed for this command."""
        tools = []
        for tool_name in self.allowed_tools:
            tool = self.registry.get(tool_name)
            if tool:
                tools.append(tool)
        return tools

    async def process(self, user_input: str) -> str:
        """Process a user input through this command's processor.

        Subclasses should override this method.
        """
        raise NotImplementedError

    async def _call_provider(
        self,
        system_prompt: str,
        user_input: str,
        tools: list | None = None,
    ) -> str:
        """Call the provider with the given system prompt and user input.

        Returns the response text.
        """
        from ..types import Message, TextBlock

        messages = [Message.user(TextBlock(text=user_input))]
        response = await self.provider.complete(
            system=system_prompt,
            messages=messages,
            tools=tools or [],
        )

        text_parts = []
        for block in response.blocks:
            if hasattr(block, "text") and block.text:
                text_parts.append(block.text)

        return "".join(text_parts)


class AskProcessor(BaseProcessor):
    """Processor for /ask command.

    Helps the user clarify and objectify their request before any work begins.
    Read-only mode: only read_file and bash (read-only) tools allowed.
    """

    async def process(self, user_input: str) -> str:
        system_prompt = self.get_system_prompt()
        response = await self._call_provider(system_prompt, user_input)

        # Store in session
        if self.session:
            self.session.messages.append(
                {"role": "user", "content": user_input, "command": "ask"}
            )
            self.session.messages.append(
                {"role": "assistant", "content": response, "command": "ask"}
            )
            self.session.touch()

        return response


class PlanProcessor(BaseProcessor):
    """Processor for /plan command.

    Creates detailed plans and saves them to docs/plans/*.md
    """

    async def process(self, user_input: str) -> str:
        system_prompt = self.get_system_prompt()
        response = await self._call_provider(system_prompt, user_input)

        # Save plan to docs/plans/
        plans_dir = Path(self.config.plans_dir)
        plans_dir.mkdir(parents=True, exist_ok=True)

        plan_name = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        plan_path = plans_dir / plan_name
        plan_path.write_text(
            f"# Plan\n\nGenerated from user input:\n\n{user_input}\n\n## Plan\n\n{response}\n",
            encoding="utf-8",
        )

        # Store in session
        if self.session:
            self.session.messages.append(
                {"role": "user", "content": user_input, "command": "plan"}
            )
            self.session.messages.append(
                {"role": "assistant", "content": response, "command": "plan"}
            )
            self.session.touch()

        return f"Plan saved to: {plan_path}\n\n{response}"


class AgentsDefaultProcessor(BaseProcessor):
    """Processor for /agents-default command.

    Breaks down user requests into tasks, creates todo list, processes one by one.
    """

    async def process(self, user_input: str) -> str:
        system_prompt = self.get_system_prompt()
        response = await self._call_provider(system_prompt, user_input)

        # Store in session
        if self.session:
            self.session.messages.append(
                {"role": "user", "content": user_input, "command": "agents-default"}
            )
            self.session.messages.append(
                {"role": "assistant", "content": response, "command": "agents-default"}
            )
            self.session.touch()

        return response


class SessionProcessor(BaseProcessor):
    """Processor for /session command.

    Creates, switches, or manages user sessions.
    """

    async def process(self, user_input: str) -> str:
        system_prompt = self.get_system_prompt()
        response = await self._call_provider(system_prompt, user_input)

        if self.session:
            self.session.messages.append(
                {"role": "user", "content": user_input, "command": "session"}
            )
            self.session.messages.append(
                {"role": "assistant", "content": response, "command": "session"}
            )
            self.session.touch()

        return response


class ScheduleProcessor(BaseProcessor):
    """Processor for /schedule command (TODO placeholder)."""

    async def process(self, user_input: str) -> str:
        return (
            "/schedule command is a TODO placeholder.\n"
            "No implementation yet. Schedule management will be added in a future release."
        )


class AgentProcessor(BaseProcessor):
    """Processor for /agent command.

    Creates or updates agents based on user requirements.
    """

    async def process(self, user_input: str) -> str:
        system_prompt = self.get_system_prompt()
        response = await self._call_provider(system_prompt, user_input)

        if self.session:
            self.session.messages.append(
                {"role": "user", "content": user_input, "command": "agent"}
            )
            self.session.messages.append(
                {"role": "assistant", "content": response, "command": "agent"}
            )
            self.session.touch()

        return response


class SkillsProcessor(BaseProcessor):
    """Processor for /skills command.

    Creates or updates skills based on user requirements.
    """

    async def process(self, user_input: str) -> str:
        system_prompt = self.get_system_prompt()
        response = await self._call_provider(system_prompt, user_input)

        if self.session:
            self.session.messages.append(
                {"role": "user", "content": user_input, "command": "skills"}
            )
            self.session.messages.append(
                {"role": "assistant", "content": response, "command": "skills"}
            )
            self.session.touch()

        return response


class HookProcessor(BaseProcessor):
    """Processor for /hook command (TODO placeholder)."""

    async def process(self, user_input: str) -> str:
        return (
            "/hook command is a TODO placeholder.\n"
            "No implementation yet. Hook management will be added in a future release."
        )


class OrchestratorProcessor(BaseProcessor):
    """Processor for /orchestrator command (TODO placeholder)."""

    async def process(self, user_input: str) -> str:
        return (
            "/orchestrator command is a TODO placeholder.\n"
            "No implementation yet. Orchestrator management will be added in a future release."
        )


class JobProcessor(BaseProcessor):
    """Processor for /job command.

    Creates process channels based on user input.
    """

    async def process(self, user_input: str) -> str:
        system_prompt = self.get_system_prompt()
        response = await self._call_provider(system_prompt, user_input)

        if self.session:
            self.session.messages.append(
                {"role": "user", "content": user_input, "command": "job"}
            )
            self.session.messages.append(
                {"role": "assistant", "content": response, "command": "job"}
            )
            self.session.touch()

        return response


# ---------------------------------------------------------------------------
# Processor registry
# ---------------------------------------------------------------------------

PROCESSOR_CLASSES: dict[str, type[BaseProcessor]] = {
    "ask": AskProcessor,
    "plan": PlanProcessor,
    "agents-default": AgentsDefaultProcessor,
    "session": SessionProcessor,
    "schedule": ScheduleProcessor,
    "agent": AgentProcessor,
    "skills": SkillsProcessor,
    "hook": HookProcessor,
    "orchestrator": OrchestratorProcessor,
    "job": JobProcessor,
}


def get_processor_class(command: str) -> type[BaseProcessor] | None:
    """Get the processor class for a given command."""
    return PROCESSOR_CLASSES.get(command)


def get_all_processors() -> list[str]:
    """Get all registered processor command names."""
    return list(PROCESSOR_CLASSES.keys())


def create_processor(
    command: str,
    config: Config,
    provider: Provider,
    registry: ToolRegistry,
    session: SessionModel | None = None,
) -> BaseProcessor | None:
    """Create a processor instance for the given command."""
    processor_class = get_processor_class(command)
    if processor_class is None:
        return None
    return processor_class(
        command=command,
        config=config,
        provider=provider,
        registry=registry,
        session=session,
    )
