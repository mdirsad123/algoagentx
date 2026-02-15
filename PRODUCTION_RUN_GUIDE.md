# AlgoAgentX Production Deployment Guide

This guide provides instructions for deploying AlgoAgentX to production using Docker and Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available
- Ports 3000, 8000, 5432, 6379 available (or modify docker-compose.yml)

## Quick Start

1. **Clone the repository and navigate to the project root**
   ```bash
   cd /path/to/algoagentx-prod/algoagentx
   ```

2. **Configure environment variables**
   - Edit `AlgoAgentXAPI/.env.prod` for backend configuration
   - Edit `AlgoAgentXApp/.env.production` for frontend configuration
   - Update database credentials, API URLs, and secrets

3. **Build and start all services**
   ```bash
   docker-compose up -d --build
   ```

4. **Run database migrations (first time only)**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

5. **Verify deployment**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Services Overview

### Database (PostgreSQL)
- **Port**: 5432
- **Volume**: postgres_data (persistent)
- **Health Check**: Automatic

### Cache (Redis)
- **Port**: 6379
- **Volume**: redis_data (persistent)
- **Health Check**: Automatic

### Backend API (FastAPI)
- **Port**: 8000
- **Workers**: 4 Gunicorn workers with Uvicorn
- **Health Check**: /health endpoint
- **Environment**: .env.prod

### Frontend (Next.js)
- **Port**: 3000
- **Build**: Standalone output
- **Health Check**: /api/health endpoint
- **Environment**: .env.production

### Background Worker (Celery)
- **Queue**: Redis-backed
- **Concurrency**: Default Celery settings
- **Environment**: .env.prod

## Production Configuration

### Environment Variables

#### Backend (.env.prod)
```env
DATABASE_URL=postgresql+asyncpg://user:password@host:port/db
REDIS_URL=redis://host:port/db
JWT_SECRET_KEY=your-secret-key
JWT_REFRESH_TOKEN_KEY=your-refresh-key
BASE_URL=https://api.yourdomain.com
ENVIRONMENT=production
DEBUG=false
```

#### Frontend (.env.production)
```env
NEXT_PUBLIC_API_SERVER=https://api.yourdomain.com
NODE_ENV=production
```

### Security Considerations

1. **Change default passwords** in docker-compose.yml
2. **Use strong JWT secrets** in production
3. **Configure proper CORS** origins in production
4. **Set up SSL/TLS** certificates
5. **Use environment-specific secrets**

### Scaling

#### Horizontal Scaling
- Add more API instances behind a load balancer
- Scale Celery workers: `docker-compose up -d --scale celery-worker=3`

#### Vertical Scaling
- Increase container resources in docker-compose.yml
- Adjust Gunicorn workers based on CPU cores

## Monitoring

### Health Checks
- All services include Docker health checks
- API endpoints: `/health` (backend), `/api/health` (frontend)

### Logs
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f frontend
```

### Resource Usage
```bash
# Check container stats
docker stats

# Check disk usage
docker system df
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change ports in docker-compose.yml
2. **Database connection**: Verify DATABASE_URL in .env.prod
3. **Build failures**: Check Docker logs and ensure dependencies are correct
4. **Memory issues**: Increase Docker memory limit or reduce workers

### Database Issues
```bash
# Reset database
docker-compose down -v
docker-compose up -d postgres
docker-compose exec api alembic upgrade head
```

### Rebuild Specific Services
```bash
# Rebuild API only
docker-compose build api
docker-compose up -d api

# Rebuild all
docker-compose down
docker-compose up -d --build
```

## Backup and Restore

### Database Backup
```bash
# Create backup
docker-compose exec postgres pg_dump -U algo_user algo_db > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U algo_user algo_db < backup.sql
```

### Volumes Backup
```bash
# Backup volumes
docker run --rm -v algoagentx_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Secrets rotated from defaults
- [ ] Database migrations run
- [ ] SSL certificates configured
- [ ] Domain DNS configured
- [ ] Monitoring set up
- [ ] Backup strategy implemented
- [ ] Load balancer configured (if scaling)

## Support

For issues or questions, check:
1. Docker logs: `docker-compose logs`
2. Health endpoints
3. Application documentation
4. Container resource usage
