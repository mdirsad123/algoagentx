# AlgoAgentX MT5 Agent Skeleton

This is a starter skeleton for the user-side Windows/VPS MT5 Agent.

Architecture:

`AlgoAgentX API Docker -> HTTPS -> AlgoAgentX MT5 Agent on Windows/VPS -> MetaTrader 5 terminal`

The API no longer needs the `MetaTrader5` Python package in production. The agent runs beside the user's MT5 terminal and reports heartbeats, polls pending commands, and posts order results.

## Environment

```env
ALGOAGENTX_API_BASE_URL=http://localhost:8000
ALGOAGENTX_MT5_AGENT_TOKEN=paste-token-generated-from-user-brokers-page
POLL_SECONDS=5
```

## Run

```bash
python agent.py
```

This skeleton does not place real trades yet. It is a safe placeholder for the installer phase.
