from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, validator
from typing import Optional, List
import os
import sys
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./algoagentx.db"
    
    # Environment detection - supports both 'env' and 'ENVIRONMENT' variables
    env: str = Field(default="development", description="Environment: development, staging, production")

    # Redis (for Celery) - Support multiple configuration methods
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # JWT
    jwt_secret_key: str = "T2kiob1GPcJwNYBhAwvNE8kr1tJaQgH4"
    jwt_refresh_token_key: str = "lM0Y9gpK1TSzpreSDJgrjqnXY9qOvog5"
    jwt_algorithm: str = "HS256"

    # SMTP (for notifications)
    smtp_email: str = "mdirsadtech7305@gmail.com"
    smtp_password: str = "ippq cczp hwkn jyrl"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    admin_notify_emails: str = ""  # Comma-separated list of admin emails

    # Base URL
    base_url: str = "http://localhost:4000"

    # Auth
    auth_service_url: Optional[str] = None  # For centralized auth if needed

    # Razorpay Payment Configuration
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    razorpay_webhook_secret: Optional[str] = None

    # CORS Configuration
    web_origin: str = Field(default="http://localhost:3000", description="Allowed web origin for CORS")

    # Security Headers
    hsts_max_age: int = Field(default=31536000, description="HSTS max age in seconds")
    hsts_include_subdomains: bool = Field(default=True, description="Include subdomains in HSTS")
    hsts_preload: bool = Field(default=True, description="Preload HSTS")

    # AI Screener Configuration
    ai_screener_enabled: bool = Field(default=False, description="Enable AI Screener functionality")
    ai_screener_sources: str = Field(default="moneycontrol,economic_times,livemint", description="Comma-separated list of news sources")
    ai_screener_top_n: int = Field(default=10, description="Number of top news/announcements to fetch per symbol")

    @property
    def ai_screener_sources_list(self) -> List[str]:
        """Get AI screener sources as a list"""
        return [source.strip() for source in self.ai_screener_sources.split(',') if source.strip()]

    def validate_ai_screener_requirements(self):
        """Validate AI Screener configuration"""
        if not self.ai_screener_enabled:
            return

        # Validate sources
        valid_sources = {'moneycontrol', 'economic_times', 'livemint', 'business_standard'}
        sources = set(self.ai_screener_sources_list)
        invalid_sources = sources - valid_sources
        
        if invalid_sources:
            logger.warning(f"Invalid AI screener sources detected: {invalid_sources}. Valid sources: {valid_sources}")
        
        # Validate top_n
        if self.ai_screener_top_n <= 0:
            logger.warning(f"AI screener top_n should be positive, got: {self.ai_screener_top_n}")

    @validator('env')
    def validate_environment(cls, v):
        """Validate environment value"""
        valid_envs = ['development', 'dev', 'staging', 'production', 'prod']
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {', '.join(valid_envs)}")
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        # Check both 'env' and 'ENVIRONMENT' for compatibility with Docker
        env_value = self.env.lower()
        return env_value == "development" or env_value == "dev"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        # Check both 'env' and 'ENVIRONMENT' for compatibility with Docker
        env_value = self.env.lower()
        return env_value == "production" or env_value == "prod"

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        env_value = self.env.lower()
        return env_value == "staging"

    def validate_production_requirements(self):
        """Validate critical environment variables for production"""
        if not self.is_production:
            return

        missing_vars = []
        required_vars = [
            ('database_url', self.database_url),
            ('jwt_secret_key', self.jwt_secret_key),
            ('razorpay_key_id', self.razorpay_key_id),
            ('razorpay_key_secret', self.razorpay_key_secret),
            ('razorpay_webhook_secret', self.razorpay_webhook_secret),
        ]

        for var_name, var_value in required_vars:
            if not var_value or var_value == "":
                missing_vars.append(var_name)

        if missing_vars:
            error_msg = f"Production environment requires the following environment variables: {', '.join(missing_vars)}"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            print("Application startup failed due to missing critical configuration.", file=sys.stderr)
            sys.exit(1)

    @property
    def database_name(self) -> str:
        """Extract database name from URL"""
        if "postgresql" in self.database_url:
            # Format: postgresql+asyncpg://user:pass@host:port/dbname
            parts = self.database_url.split("/")
            if len(parts) >= 4:
                db_part = parts[-1].split("@")[0] if "@" in parts[-1] else parts[-1]
                return db_part
        return "unknown"
    
    @property
    def database_host(self) -> str:
        """Extract database host from URL"""
        if "postgresql" in self.database_url:
            parts = self.database_url.split("@")
            if len(parts) >= 2:
                host_part = parts[1].split(":")[0] if ":" in parts[1] else parts[1].split("/")[0]
                return host_part
        return "unknown"
    
    @property
    def database_port(self) -> int:
        """Extract database port from URL"""
        if "postgresql" in self.database_url:
            parts = self.database_url.split("@")
            if len(parts) >= 2 and ":" in parts[1]:
                port_part = parts[1].split(":")[1].split("/")[0]
                try:
                    return int(port_part)
                except ValueError:
                    return 5432
        return 5432

    @property
    def masked_database_url(self) -> str:
        """Return database URL with masked password"""
        if "postgresql" in self.database_url:
            # Replace password with asterisks
            masked = self.database_url
            if "@" in masked:
                protocol, rest = masked.split("://", 1)
                if ":" in rest and "@" in rest:
                    user_pass, host_port = rest.split("@", 1)
                    if ":" in user_pass:
                        user, _ = user_pass.split(":", 1)
                        masked = f"{protocol}://{user}:****@{host_port}"
            return masked
        return self.database_url

    @property
    def allowed_origins(self) -> List[str]:
        """Get allowed CORS origins based on environment"""
        if self.is_development:
            return ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"]
        else:
            # Production and staging - only allow configured web origin
            return [self.web_origin]

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='allow'  # Allow extra fields from env
    )


settings = Settings()

# Validate production requirements on import
settings.validate_production_requirements()



