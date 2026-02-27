from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Note: Model imports are handled by alembic/env.py and app.db.models.__init__.py
# to avoid circular import issues
