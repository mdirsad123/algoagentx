# AlgoAgentX API

FastAPI backend for the AlgoAgentX trading platform.

## Local Development Setup

### Prerequisites
1. **PostgreSQL Database**: Ensure PostgreSQL is running on the configured host/port
   - Default: `localhost:5432` (or set DATABASE_URL in .env)
   - Create database user/password and database as per your configuration
   
2. **Python 3.8+** with pip installed

### Quick Start

1. **Start Database Services**
   ```bash
   # Start PostgreSQL and Redis using docker-compose
   docker-compose up postgres redis -d
   
   # Wait a few seconds for services to be ready
   ```

2. **Install Dependencies**
   ```bash
   cd AlgoAgentXAPI
   pip install -r requirements.txt
   ```

3. **Configure Database (Optional)**
   - Copy `.env.example` to `.env` if you need custom settings
   - Or use default DATABASE_URL: `postgresql+asyncpg://algo_user:algo_password@localhost:5432/algo_db`

4. **Start the API**
   ```bash
   cd AlgoAgentXAPI
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   start app
   cd AlgoAgentXApp
   npm run dev
   ```

4. **Health Checks**
   - Database: http://localhost:8000/health/db
   - General: http://localhost:8000/health

5. **Test Authentication**
   - Open Swagger UI: http://localhost:8000/docs
   - Try signup/login endpoints - should return access_token (not 500)

### Test Credentials
```
Email: test@example.com
Password: password123
```

### Optional: Redis (for background tasks)
```bash
docker run -d -p 6379:6379 --name algoagentx-redis redis:alpine
```
