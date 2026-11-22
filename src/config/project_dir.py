"""
Project directory Singleton.

Provides a single source of truth for the root/workspace directories
across the entire application. The Project class is a Singleton: only one
instance ever exists, and all components read the directories from it.

Two directories are tracked:
- **root_dir**: Fixed root where global `.agents` (skills/agents) live.
  Set once at startup and stays constant for the session.
- **workspace_dir**: Changeable working directory. Can be changed at
  runtime via the `/workspace` slash command or `change_workspace` tool.

Skills and agents are loaded from both locations, with workspace `.agents`
taking priority over root `.agents`.
"""

from __future__ import annotations

from pathlib import Path


class Project:
    """Singleton that holds root_dir and workspace_dir.

    Use :meth:`get_instance` to obtain the single instance, and
    :meth:`set_root_dir` / :meth:`set_workspace_dir` to update them.
    """

    _instance: Project | None = None

    def __new__(cls, root_dir: Path | None = None, workspace_dir: Path | None = None) -> Project:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, root_dir: Path | None = None, workspace_dir: Path | None = None) -> None:
        if self._initialized:
            return
        cwd = Path.cwd()
        self.root_dir = root_dir or cwd
        self.workspace_dir = workspace_dir or cwd
        self._initialized = True

    @classmethod
    def get_instance(cls) -> Project:
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = Project()
        return cls._instance

    @classmethod
    def get_root_dir(cls) -> Path:
        """Return the fixed root directory as a :class:`Path`."""
        return cls.get_instance().root_dir

    @classmethod
    def get_workspace_dir(cls) -> Path:
        """Return the current workspace directory as a :class:`Path`."""
        return cls.get_instance().workspace_dir

    @classmethod
    def set_root_dir(cls, new_root_dir: Path | str) -> Project:
        """Set the fixed root directory. Should only be called once at startup."""
        instance = cls.get_instance()
        instance.root_dir = Path(new_root_dir).resolve()
        return instance

    @classmethod
    def set_workspace_dir(cls, new_workspace_dir: Path | str) -> Project:
        """Update the changeable workspace directory."""
        instance = cls.get_instance()
        instance.workspace_dir = Path(new_workspace_dir).resolve()
        return instance

    def get_products_dir(self) -> Path:
        """Return the products directory (same as workspace dir)."""
        return self.workspace_dir

    def __repr__(self) -> str:
        return f"Project(root_dir={self.root_dir}, workspace_dir={self.workspace_dir})"


# Module-level helper for backward compatibility
def get_project_dir() -> Project:
    """Return the singleton Project instance."""
    return Project.get_instance()


project = Project.get_instance()  # Global singleton instance
