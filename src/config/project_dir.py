"""
Project directory Singleton.

Provides a single source of truth for the workspace/project directory
across the entire application. The Project class is a Singleton: only one
instance ever exists, and all components read the project directory from it.
"""

from __future__ import annotations

from pathlib import Path


class Project:
    """Singleton that holds the project/workspace directory.

    Use :meth:`get_instance` to obtain the single instance, and
    :meth:`set_project_dir` / :meth:`get_project_dir` to read or change
    the directory.  All application components should read the project
    directory from this singleton rather than constructing their own
    :class:`Path` objects.
    """

    _instance: Project | None = None

    def __new__(cls, project_root: Path | None = None) -> Project:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, project_root: Path | None = None) -> None:
        if self._initialized:
            return
        self.project_root = project_root or Path.cwd()
        self._initialized = True

    @classmethod
    def get_instance(cls) -> Project:
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = Project()
        return cls._instance

    @classmethod
    def get_project_dir(cls) -> Path:
        """Return the current project directory as a :class:`Path`."""
        return cls.get_instance().project_root

    @classmethod
    def set_project_dir(cls, new_project_root: Path | str) -> Project:
        """Update the project directory and return the singleton instance."""
        instance = cls.get_instance()
        instance.project_root = Path(new_project_root).resolve()
        return instance

    @classmethod
    def updated_project_dir(cls, new_project_root: Path | str) -> Project:
        """Alias for :meth:`set_project_dir` (kept for backward compat)."""
        return cls.set_project_dir(new_project_root)

    def get_products_dir(self) -> Path:
        """Return the products directory (same as project root)."""
        return self.project_root

    def __repr__(self) -> str:
        return f"Project({self.project_root})"


# Module-level helper for backward compatibility
def get_project_dir() -> Project:
    """Return the singleton Project instance."""
    return Project.get_instance()


project = Project.get_instance()  # Global singleton instance
