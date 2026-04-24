"""Application configuration via environment variables and defaults."""

from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(path: Path | str) -> Path:
    """Resolve paths relative to the repository root."""
    resolved = Path(path).expanduser()
    if resolved.is_absolute():
        return resolved.resolve()
    return (PROJECT_ROOT / resolved).resolve()


class Settings(BaseSettings):
    """ModForge backend configuration."""

    # Paths
    workspace_dir: Path = PROJECT_ROOT / "workspaces"
    tools_dir: Path = PROJECT_ROOT / "tools"

    # Decompiler
    decompiler: str = "cfr"  # cfr | fernflower | procyon
    java_path: str = "java"
    cfr_jar: str = "cfr-0.152.jar"

    # Server
    host: str = "127.0.0.1"
    port: int = 8420
    ai_port: int = 8421

    # General
    auto_decompile: bool = True
    max_jar_size_mb: int = 200

    model_config = {"env_prefix": "MODFORGE_"}

    def normalize_paths(self) -> None:
        """Resolve configurable paths to absolute locations."""
        self.workspace_dir = resolve_project_path(self.workspace_dir)
        self.tools_dir = resolve_project_path(self.tools_dir)


settings = Settings()
settings.normalize_paths()
