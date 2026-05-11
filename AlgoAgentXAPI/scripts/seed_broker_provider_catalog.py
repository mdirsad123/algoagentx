"""Seed Broker Provider catalog for BROKER-PRO-1/2.

Preferred for local/dev: run the SQL migration instead:
  scripts/broker_pro_1_broker_provider_catalog_safe_migration.sql
"""
from pathlib import Path

print(Path(__file__).with_name('broker_pro_1_broker_provider_catalog_safe_migration.sql').read_text())
