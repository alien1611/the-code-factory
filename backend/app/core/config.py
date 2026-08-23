from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Information
    PROJECT_NAME: str = "Evidence-Driven Verification Engine"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Backend Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Database
    DATABASE_URL: str = "sqlite:///./evidence_verifier.db"

    # GitHub & OAuth
    GITHUB_TOKEN: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    GITHUB_REDIRECT_URI: str = "http://localhost:5173/oauth/callback"
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_WEBHOOK_SECRET: str | None = None

    # Gemini LLM (Supports 1-5 keys or comma-separated list with automatic failover)
    GEMINI_API_KEY: str | None = None
    GEMINI_API_KEYS: str | list[str] | None = None
    GEMINI_API_KEY_1: str | None = None
    GEMINI_API_KEY_2: str | None = None
    GEMINI_API_KEY_3: str | None = None
    GEMINI_API_KEY_4: str | None = None
    GEMINI_API_KEY_5: str | None = None
    GEMINI_MODEL: str = "gemini-3.6-flash"

    def get_gemini_api_keys(self) -> list[str]:
        keys = []
        if isinstance(self.GEMINI_API_KEYS, list):
            keys.extend(self.GEMINI_API_KEYS)
        elif isinstance(self.GEMINI_API_KEYS, str) and self.GEMINI_API_KEYS.strip():
            keys.extend([k.strip() for k in self.GEMINI_API_KEYS.split(",") if k.strip()])

        for k in [self.GEMINI_API_KEY, self.GEMINI_API_KEY_1, self.GEMINI_API_KEY_2, self.GEMINI_API_KEY_3, self.GEMINI_API_KEY_4, self.GEMINI_API_KEY_5]:
            if k and k.strip() and k.strip() not in keys:
                keys.append(k.strip())
        return keys

    # Docker Sandbox Execution
    DOCKER_ENABLED: bool = False
    DOCKER_SANDBOX_IMAGE: str = "evidence-verifier-sandbox:latest"
    DOCKER_TIMEOUT_SECONDS: int = 120
    DOCKER_MEMORY_LIMIT: str = "512m"
    DOCKER_CPU_LIMIT: float = 1.0

    # Workspace & File Management
    WORKSPACE_BASE_DIR: str = "./temp_workspaces"
    CLEANUP_WORKSPACE_ON_FINISH: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

# Ensure absolute workspace directory
workspace_path = Path(settings.WORKSPACE_BASE_DIR)
if not workspace_path.is_absolute():
    settings.WORKSPACE_BASE_DIR = str(Path(__file__).resolve().parent.parent.parent / settings.WORKSPACE_BASE_DIR)
