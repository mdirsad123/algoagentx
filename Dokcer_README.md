# AlgoAgentX Docker Production Setup

This package contains Docker files for your current AlgoAgentX structure:

- `AlgoAgentXAPI` = FastAPI backend
- `AlgoAgentXApp` = Next.js frontend
- PostgreSQL container
- Redis container
- Optional Celery worker

## Files

```text
api/Dockerfile.prod                 -> copy to AlgoAgentXAPI/Dockerfile.prod
api/.dockerignore                   -> copy to AlgoAgentXAPI/.dockerignore
app/Dockerfile.prod                 -> copy to AlgoAgentXApp/Dockerfile.prod
app/.dockerignore                   -> copy to AlgoAgentXApp/.dockerignore
docker-compose.yml                  -> copy to project root
.env.prod.example                   -> copy to project root, then rename/copy as .env.prod
nginx/algoagentx.nginx.conf         -> optional Nginx reverse proxy template
scripts/deploy_commands.md          -> command checklist
```

## Important production notes

1. Do not commit `.env.prod`.
2. Do not commit `node_modules`.
3. Do not expose PostgreSQL publicly in production.
4. Keep `ADMIN_OTP_ENABLED=true` in production.
5. Keep `GOOGLE_ADMIN_LOGIN_ENABLED=false` unless you later build an admin allowlist plus 2FA.
6. Update Google OAuth redirect/origin settings for production domains.
7. Update Razorpay webhook URL to the production API domain.
8. Run DB migrations before testing production flows.
9. Take DB backup before every major migration.

## Recommended production domains

```text
https://app.yourdomain.com  -> frontend
https://api.yourdomain.com  -> backend
```

Set these values in `.env.prod`:

```env
FRONTEND_URL=https://app.yourdomain.com
WEB_ORIGIN=https://app.yourdomain.com
BASE_URL=https://api.yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_API_SERVER=https://api.yourdomain.com
```
