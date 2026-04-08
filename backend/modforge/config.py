"""Application configuration via environment variables and defaults."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ModForge backend configuration."""

    # Paths
    workspace_dir: Path = Path("./workspaces")
    tools_dir: Path = Path("./tools")

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


settings = Settings()
