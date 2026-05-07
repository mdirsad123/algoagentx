from fastapi import APIRouter
from . import auth, users, strategies, backtests, signals, metrics, instruments, jobs, market_data, credits, billing, payments, subscriptions, ai_screener, notifications, strategy_requests, admin_strategy_requests, ai_screener_jobs, admin, admin_market_data, support_tickets, public, dashboard
from . import admin_pricing
from . import admin_coupons
from . import admin_credit_rules
from . import admin_credit_packs
from . import admin_billing
from . import settings
from . import admin_risk_engine
from . import admin_strategy_runtime_presets
from . import market_master
from . import admin_email
from . import live_runner
from . import live_trading_preview
from . import profile_settings
from . import admin_strategy_gate
from . import broker_accounts, live_deployments, live_signals, live_orders, live_positions, live_logs, webhooks, admin_live, admin_live_settings, admin_live_trading_actions, admin_broker_providers, broker_instruments, live_approvals

api_router = APIRouter()

# Include all API routes (read-only, no auth required)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(instruments.router, prefix="/instruments", tags=["instruments"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(backtests.router, prefix="/backtests", tags=["backtests"])
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(credits.router, prefix="/credits", tags=["credits"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(billing.admin_router, prefix="/admin/billing", tags=["admin-billing"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(public.router, prefix="/public", tags=["public"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(profile_settings.profile_router, prefix="/profile", tags=["profile"])
api_router.include_router(profile_settings.settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(settings.admin_router, prefix="/admin/settings", tags=["admin-settings"])
api_router.include_router(ai_screener.router, prefix="/ai-screener", tags=["ai-screener"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(strategy_requests.router, prefix="/strategy-requests", tags=["strategy-requests"])
api_router.include_router(admin_strategy_requests.router, prefix="/admin/strategy-requests", tags=["admin-strategy-requests"])
api_router.include_router(ai_screener_jobs.router, prefix="/ai-screener-jobs", tags=["ai-screener-jobs"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_email.router, prefix="/admin/email", tags=["admin-email"])
api_router.include_router(admin_market_data.router, prefix="/admin/market-data", tags=["admin-market-data"])
api_router.include_router(admin_risk_engine.router, prefix="/admin/risk-engine", tags=["admin-risk-engine"])
api_router.include_router(market_master.router, prefix="/market-master", tags=["market-master"])
api_router.include_router(market_master.admin_router, prefix="/admin/market-master", tags=["admin-market-master"])
api_router.include_router(admin_pricing.router, prefix="/admin/pricing", tags=["admin-pricing"])
api_router.include_router(admin_coupons.router, prefix="/admin/coupons", tags=["admin-coupons"])
api_router.include_router(admin_credit_rules.router, prefix="/admin/credit-rules", tags=["admin-credit-rules"])
api_router.include_router(admin_credit_packs.router, prefix="/admin/credit-packs", tags=["admin-credit-packs"])
api_router.include_router(admin_billing.router, prefix="/admin/billing", tags=["admin-billing-audit"])
api_router.include_router(admin_strategy_gate.router, prefix="/admin/strategies", tags=["admin-strategy-gate"])
api_router.include_router(admin_strategy_runtime_presets.router, prefix="/admin", tags=["admin-strategy-runtime-presets"])
api_router.include_router(support_tickets.router, prefix="/support-tickets", tags=["support-tickets"])
api_router.include_router(support_tickets.admin_router, prefix="/admin/support-tickets", tags=["admin-support-tickets"])
api_router.include_router(broker_accounts.router, prefix="/broker-accounts", tags=["broker-accounts"])
api_router.include_router(broker_instruments.router, prefix="/broker-instruments", tags=["broker-instruments"])
api_router.include_router(live_deployments.router, prefix="/live/deployments", tags=["live-deployments"])
api_router.include_router(live_signals.router, prefix="/live/signals", tags=["live-signals"])
api_router.include_router(live_orders.router, prefix="/live/orders", tags=["live-orders"])
api_router.include_router(live_positions.router, prefix="/live/positions", tags=["live-positions"])
api_router.include_router(live_logs.router, prefix="/live/logs", tags=["live-logs"])
api_router.include_router(live_runner.router, prefix="/live/runner", tags=["live-runner"])
api_router.include_router(live_trading_preview.router, prefix="/live-trading", tags=["live-trading-preview"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(live_approvals.router, prefix="/live-approvals", tags=["live-approvals"])
api_router.include_router(live_approvals.admin_router, prefix="/admin/live-approvals", tags=["admin-live-approvals"])

api_router.include_router(admin_live.router, prefix="/admin/live", tags=["admin-live-trading"])
api_router.include_router(admin_live_settings.router, prefix="/admin/live-settings", tags=["admin-live-settings"])
api_router.include_router(admin_live_trading_actions.router, prefix="/admin/live-trading", tags=["admin-live-emergency"])
api_router.include_router(
    admin_broker_providers.router,
    prefix="/admin/broker-providers",
    tags=["admin-broker-providers"],
)