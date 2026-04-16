"""Configuration management for ShiftZero"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # AWS Bedrock
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None  # For temporary credentials
    aws_profile: str | None = None
    bedrock_model_id: str = "anthropic.claude-opus-4-6"

    # PagerDuty
    pagerduty_api_key: str
    pagerduty_webhook_secret: str

    # Kubernetes
    kubeconfig: str | None = None

    # Database
    database_url: str = "postgresql://shiftzero:password@localhost:5432/shiftzero"

    # Slack
    slack_bot_token: str | None = None
    slack_oncall_channel: str = "#oncall-alerts"

    # Safety Settings
    max_auto_restarts_per_hour: int = 3
    confidence_threshold_auto_remediate: float = 0.85
    confidence_threshold_escalate: float = 0.70
    dry_run_mode: bool = False

    # Application
    log_level: str = "INFO"
    webhook_port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
