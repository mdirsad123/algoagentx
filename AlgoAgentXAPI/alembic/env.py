from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models to ensure they are registered with Base.metadata
# This is critical - without this, alembic won't detect any models
try:
    import app.db.models.users
    import app.db.models.strategies
    import app.db.models.instruments
    import app.db.models.market_data
    import app.db.models.backtests  # Contains PerformanceMetric
    import app.db.models.trades
    import app.db.models.metrics
    import app.db.models.equity_curve
    import app.db.models.pnl_calendar
    import app.db.models.job_status
    import app.db.models.user_credits
    import app.db.models.credit_transactions
    import app.db.models.user_subscriptions
    import app.db.models.plans
    import app.db.models.payments
    import app.db.models.notifications
    import app.db.models.strategy_requests
    import app.db.models.screener_news
    import app.db.models.screener_announcements
    import app.db.models.screener_runs
except ImportError as e:
    print(f"Warning: Could not import some models: {e}")

# add your model's MetaData object here
# for 'autogenerate' support
from app.db.base import Base
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    
    # Configure context with SQLite-specific options if needed
    context_config = {
        "url": url,
        "target_metadata": target_metadata,
        "literal_binds": True,
        "dialect_opts": {"paramstyle": "named"},
        "compare_type": True,
    }
    
    # Add render_as_batch for SQLite
    if url and "sqlite" in url:
        context_config["render_as_batch"] = True
    
    context.configure(**context_config)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    # Use the database URL from environment variables
    # The config should read from the .env file automatically
    # If not, we'll use the default from settings
    
    from app.core.config import settings
    # Convert async URL to sync for migrations
    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    configuration["sqlalchemy.url"] = sync_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    def do_migrations(connection):
        # Configure context with SQLite-specific options if needed
        context_config = {
            "connection": connection,
            "target_metadata": target_metadata,
            "compare_type": True,
        }
        
        # Add render_as_batch for SQLite
        if "sqlite" in str(connection.engine.url):
            context_config["render_as_batch"] = True
            
        context.configure(**context_config)

        with context.begin_transaction():
            context.run_migrations()

    with connectable.connect() as connection:
        do_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()