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
    api_base_url: str = "http://localhost:8000"
    public_api_base_url: str = "http://localhost:8000"
    broker_redirect_base_url: str = "http://localhost:8000"

    # Auth
    auth_service_url: Optional[str] = None  # For centralized auth if needed

    # Upstox OAuth Configuration
    upstox_client_id: Optional[str] = None
    upstox_client_secret: Optional[str] = None
    upstox_redirect_uri: Optional[str] = None

    # cTrader Open API OAuth Configuration
    ctrader_client_id: Optional[str] = None
    ctrader_client_secret: Optional[str] = None
    ctrader_redirect_uri: Optional[str] = None
    ctrader_env: str = "demo"
    ctrader_oauth_authorize_url: str = "https://openapi.ctrader.com/apps/auth"
    ctrader_oauth_token_url: str = "https://openapi.ctrader.com/apps/token"
    # Optional REST-compatible endpoints for account/symbol sync. cTrader Open API trading data is primarily protobuf/TCP; set these if using a REST bridge/proxy.
    ctrader_accounts_url: Optional[str] = None
    ctrader_account_info_url: Optional[str] = None
    ctrader_symbols_url: Optional[str] = None
    # Optional REST-compatible endpoint/bridge for safe cTrader DEMO order execution.
    # cTrader Open API order routing is protobuf/TCP; keep this unset until a verified bridge/transport is configured.
    ctrader_demo_order_url: Optional[str] = None
    ctrader_demo_trading_enabled: bool = True
    ctrader_live_trading_enabled: bool = False
    live_approval_strict_market_scope: bool = Field(default=False, description="When true, live approval approved_markets restrict deployment instruments/markets")

    # MT5 execution architecture
    # AGENT is the production-safe default. LOCAL is only for Windows development where MetaTrader5 is installed beside the API.
    mt5_execution_mode: str = Field(default="AGENT", description="MT5 execution mode: AGENT or LOCAL")
    mt5_agent_heartbeat_stale_seconds: int = Field(default=90, description="Seconds after which an MT5 agent heartbeat is considered stale")

    # Live auto strategy runner
    live_runner_enabled: bool = Field(default=True, description="Enable background live strategy auto runner")
    live_runner_interval_seconds: int = Field(default=1, description="Auto runner scheduler scan interval in seconds; 1s keeps candle-close execution latency low")
    live_broker_sync_enabled: bool = Field(default=True, description="Enable background broker auto sync loop")
    live_broker_sync_loop_seconds: int = Field(default=5, description="Broker auto sync scheduler loop interval in seconds")

    # Event-driven live trading pipeline. These flags default to the legacy
    # scheduler so a deployment can be rolled forward (or back) without a code
    # change. Dedicated Docker workers refuse to do work unless their matching
    # flag is enabled.
    live_event_pipeline_enabled: bool = Field(default=False, description="Enable the Redis-stream live trading pipeline")
    live_market_worker_enabled: bool = Field(default=False, description="Enable persistent cTrader market-data worker")
    live_strategy_stream_enabled: bool = Field(default=False, description="Enable Redis Stream strategy worker")
    live_reconcile_worker_enabled: bool = Field(default=False, description="Enable dedicated slow broker reconciliation worker")
    ctrader_persistent_connection_enabled: bool = Field(default=False, description="Route cTrader market/order traffic through persistent sessions")
    live_legacy_runner_enabled: bool = Field(default=True, description="Keep the legacy scheduler available for rollback")

    live_candle_stream: str = Field(default="live:candle_closed", description="Redis Stream for closed-candle events")
    live_order_request_stream: str = Field(default="live:ctrader_order_requests", description="Redis Stream for persistent cTrader order requests")
    live_strategy_consumer_group: str = Field(default="live-strategy-runners", description="Closed-candle strategy consumer group")
    live_order_consumer_group: str = Field(default="live-ctrader-order-gateway", description="cTrader order gateway consumer group")
    live_stream_maxlen: int = Field(default=100000, description="Approximate max Redis Stream length")
    live_worker_concurrency: int = Field(default=8, description="Maximum concurrently processed deployment events")
    live_pending_reclaim_idle_ms: int = Field(default=30000, description="Minimum idle time before reclaiming pending stream entries")
    live_worker_health_ttl_seconds: int = Field(default=30, description="Worker health heartbeat TTL")
    live_order_dedupe_ttl_seconds: int = Field(default=86400, description="TTL for atomic external-order claims/results")

    live_candle_fallback_first_seconds: int = Field(default=3, description="First missing-candle recovery delay")
    live_candle_fallback_second_seconds: int = Field(default=8, description="Second missing-candle recovery delay")
    live_market_deployment_scan_seconds: int = Field(default=15, description="Seconds between active deployment registry refreshes")
    live_market_bootstrap_candles: int = Field(default=300, description="Initial cTrader closed-candle bootstrap count")
    live_market_backfill_candles: int = Field(default=5, description="Small reconnect/watchdog backfill count")

    ctrader_heartbeat_seconds: int = Field(default=8, description="Persistent cTrader application heartbeat interval")
    ctrader_request_timeout_seconds: int = Field(default=15, description="Persistent cTrader request timeout")
    ctrader_order_timeout_seconds: int = Field(default=15, description="Persistent cTrader order acknowledgement/fill timeout")
    ctrader_metadata_cache_seconds: int = Field(default=3600, description="cTrader full-symbol metadata cache TTL")

    broker_state_max_age_seconds: int = Field(default=3, description="Maximum cached broker-state age on the cTrader hot path")
    live_reconcile_interval_seconds: int = Field(default=30, description="Dedicated broker reconciliation interval")
    live_latency_trace_enabled: bool = Field(default=True, description="Collect and persist T0-T17 live execution traces")
    live_latency_trace_retention_days: int = Field(default=30, description="Detailed live trace retention window")

    # Real-time alerting / Telegram (Phase 1)
    telegram_bot_token: str = ""
    telegram_default_chat_id: str = ""
    telegram_timeout_seconds: int = 10

    # Twilio WhatsApp alert delivery (small post-Phase-2A enhancement).
    # Values are loaded from environment variables; never hard-code production credentials.
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_whatsapp_number: str = ""
    twilio_to_whatsapp_number: str = ""
    # Legacy single template SID (kept for backwards compatibility).
    twilio_content_sid: str = ""
    # Recommended Phase 2B templates: one for approach alerts and one for reached/triggered alerts.
    twilio_content_sid_approaching: str = ""
    twilio_content_sid_triggered: str = ""
    twilio_timeout_seconds: int = 10

    alert_worker_heartbeat_ttl_seconds: int = 30
    alert_feed_stale_seconds: int = 15
    alert_quote_poll_interval_ms: int = 250

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



