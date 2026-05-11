from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, validator
from typing import Optional, List
import os
import sys
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://algo_user:algo_password@localhost:5432/algo_db"
    
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
    access_token_expire_minutes: int = 1440
    remember_me_expire_days: int = 30

    # Google OAuth / auth hardening
    google_auth_enabled: bool = False
    google_client_id: str = ""
    google_allowed_email_domain: str = ""
    google_admin_login_enabled: bool = False
    frontend_url: str = "http://localhost:3000"
    password_reset_token_minutes: int = 30

    # Admin email OTP login security
    admin_otp_enabled: bool = True
    admin_otp_expire_minutes: int = 10
    admin_otp_max_attempts: int = 5
    admin_otp_resend_cooldown_seconds: int = 60

    # SMTP / Email notifications (do not hardcode credentials; use .env)
    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "AlgoAgentX"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 10
    # Backward compatibility for older modules/env names
    smtp_email: str = ""
    admin_notify_emails: str = ""  # Comma-separated list of admin emails

    # Base URL
    base_url: str = "http://localhost:4000"

    # Auth
    auth_service_url: Optional[str] = None  # For centralized auth if needed

    # Upstox OAuth Configuration
    upstox_client_id: Optional[str] = None
    upstox_client_secret: Optional[str] = None
    upstox_redirect_uri: Optional[str] = None

    # MT5 execution architecture
    # AGENT is the production-safe default. LOCAL is only for Windows development where MetaTrader5 is installed beside the API.
    mt5_execution_mode: str = Field(default="AGENT", description="MT5 execution mode: AGENT or LOCAL")
    mt5_agent_heartbeat_stale_seconds: int = Field(default=90, description="Seconds after which an MT5 agent heartbeat is considered stale")

    # Live auto strategy runner
    live_runner_enabled: bool = Field(default=True, description="Enable background live strategy auto runner")
    live_runner_interval_seconds: int = Field(default=10, description="Auto runner loop interval in seconds")
    live_broker_sync_enabled: bool = Field(default=True, description="Enable background broker auto sync loop")
    live_broker_sync_loop_seconds: int = Field(default=5, description="Broker auto sync scheduler loop interval in seconds")

    # Razorpay Payment Configuration
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    razorpay_webhook_secret: Optional[str] = None

    # Credit top-up configuration
    credits_allow_custom_topup: bool = True
    credits_min_custom_topup: int = 1
    credits_max_custom_topup: int = 100000
    credits_topup_packs_json: Optional[str] = None

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
        insecure_vars = []
        required_vars = [
            ('database_url', self.database_url),
            ('jwt_secret_key', self.jwt_secret_key),
            ('razorpay_key_id', self.razorpay_key_id),
            ('razorpay_key_secret', self.razorpay_key_secret),
            ('razorpay_webhook_secret', self.razorpay_webhook_secret),
        ]

        default_jwt_secret = "T2kiob1GPcJwNYBhAwvNE8kr1tJaQgH4"
        default_refresh_secret = "lM0Y9gpK1TSzpreSDJgrjqnXY9qOvog5"

        for var_name, var_value in required_vars:
            if not var_value or var_value == "":
                missing_vars.append(var_name)

        if self.jwt_secret_key == default_jwt_secret:
            insecure_vars.append('jwt_secret_key')
        if self.jwt_refresh_token_key == default_refresh_secret:
            insecure_vars.append('jwt_refresh_token_key')
        if 'localhost' in str(self.web_origin).lower() or '127.0.0.1' in str(self.web_origin).lower():
            insecure_vars.append('web_origin')
        if 'localhost' in str(self.frontend_url).lower() or '127.0.0.1' in str(self.frontend_url).lower():
            insecure_vars.append('frontend_url')

        if missing_vars or insecure_vars:
            parts = []
            if missing_vars:
                parts.append(f"missing: {', '.join(missing_vars)}")
            if insecure_vars:
                parts.append(f"must be changed from development defaults: {', '.join(insecure_vars)}")
            error_msg = "Production environment configuration is not safe (" + "; ".join(parts) + ")"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            print("Application startup failed due to missing or unsafe production configuration.", file=sys.stderr)
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
        configured = [origin.strip() for origin in str(self.web_origin or "").split(",") if origin.strip()]
        if self.is_development:
            dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"]
            return list(dict.fromkeys(dev_origins + configured))
        return configured or [self.web_origin]

    model_config = ConfigDict(
        env_file=(".env", ".env.local"),
        case_sensitive=False,
        extra='allow'  # Allow extra fields from env
    )


settings = Settings()

# Check for .env file in development
if settings.is_development:
    env_file_path = ".env"
    if not os.path.exists(env_file_path):
        logger.warning(".env missing, using default DATABASE_URL and configuration values")
        logger.info(f"Current DATABASE_URL: {settings.masked_database_url}")
        logger.info("To customize configuration, copy .env.example to .env and modify as needed")

# Validate production requirements on import
settings.validate_production_requirements()





