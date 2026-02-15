# AlgoAgentX API - Production Deployment Guide

This guide covers the production-safe deployment configuration for the AlgoAgentX API with Redis fallback support.

## 🎯 Overview

The AlgoAgentX API has been enhanced with production-grade features including:

- **Redis Fallback Support**: Jobs execute reliably even without Redis
- **Environment Validation**: Critical variables validated at startup
- **Security Headers**: Comprehensive security configuration
- **Request Tracking**: Enhanced logging and monitoring
- **Job Retry Policy**: Automatic retry with exponential backoff
- **Database Cleanup**: Automated cleanup of old job records

## 🚀 Quick Start

### 1. Environment Configuration

Copy the production template and configure your environment:

```bash
cp .env.production.template .env.production
```

Edit `.env.production` with your actual values:

```bash
# Database Configuration (REQUIRED)
DATABASE_URL="postgresql+asyncpg://algo_user:your_secure_password@your-db-host:5432/algo_production"

# JWT Configuration (REQUIRED)
JWT_SECRET_KEY="your-very-secure-jwt-secret-key-here-minimum-32-characters"
JWT_REFRESH_TOKEN_KEY="your-very-secure-refresh-token-key-here-minimum-32-characters"

# Razorpay Payment Configuration (REQUIRED)
RAZORPAY_KEY_ID="your_razorpay_key_id_here"
RAZORPAY_KEY_SECRET="your_razorpay_key_secret_here"
RAZORPAY_WEBHOOK_SECRET="your_razorpay_webhook_secret_here"

# Environment (REQUIRED)
ENV="production"

# Web Origin for CORS (REQUIRED in production)
WEB_ORIGIN="https://your-frontend-domain.com"

# Redis Configuration (REQUIRED for Celery)
REDIS_URL="redis://your-redis-host:6379/0"
```

### 2. Database Setup

Run migrations:

```bash
alembic upgrade head
```

### 3. Start Services

#### With Redis (Recommended)

```bash
# Start Redis
redis-server

# Start Celery worker
celery -A app.celery_app.celery_app worker --loglevel=info

# Start API
uvicorn app.main:app --host 0.0.0.0 --port 4000 --workers 4
```

#### Without Redis (Fallback Mode)

```bash
# Start API (will use direct execution fallback)
uvicorn app.main:app --host 0.0.0.0 --port 4000 --workers 4
```

## 🔧 Configuration Details

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string | - |
| `JWT_SECRET_KEY` | ✅ | JWT signing secret | - |
| `RAZORPAY_KEY_ID` | ✅ | Razorpay API key | - |
| `RAZORPAY_KEY_SECRET` | ✅ | Razorpay API secret | - |
| `ENV` | ✅ | Environment: development/staging/production | development |
| `WEB_ORIGIN` | ✅ (prod) | Allowed CORS origin | http://localhost:3000 |
| `REDIS_URL` | ✅ (for Celery) | Redis connection string | redis://localhost:6379/0 |

### Security Configuration

#### CORS Settings

- **Development**: Allows localhost origins (3000, 3001)
- **Production**: Only allows configured `WEB_ORIGIN`

#### Security Headers

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- **HSTS**: Enabled for production/staging
- **CSP**: Content Security Policy for production

#### Request Tracking

- Unique request IDs for debugging
- Enhanced logging with user/job context
- Response time tracking
- Error correlation

## 🔄 Job Execution Architecture

### Redis Available (Normal Mode)

```
API Request → Celery Queue → Redis → Celery Worker → Database
```

### Redis Unavailable (Fallback Mode)

```
API Request → Direct Execution → Database
```

### Job Lifecycle

1. **Job Creation**: Job record created in database
2. **Queue Submission**: Try Celery, fallback to direct execution
3. **Execution**: Backtest runs with progress tracking
4. **Result Storage**: Results saved to database
5. **Status Updates**: Real-time progress updates

### Retry Policy

- **Max Retries**: 3 attempts
- **Backoff**: Exponential (60s, 120s, 240s)
- **Auto-Refund**: Credits refunded on permanent failure
- **Status Tracking**: Retry count and failure reasons

## 📊 Monitoring & Health Checks

### Health Check Endpoints

- `GET /health` - Basic health check
- `GET /health/redis` - Redis-specific health check
- `GET /ready` - Readiness check for orchestration
- `GET /system/status` - Comprehensive system status

### System Status Response

```json
{
  "redis": {
    "redis_available": true,
    "ping": "PONG"
  },
  "celery_available": true,
  "job_statistics": {
    "total_jobs": 150,
    "pending_jobs": 5,
    "running_jobs": 2,
    "completed_jobs": 140,
    "failed_jobs": 3,
    "retry_jobs": 0
  },
  "fallback_mode": false,
  "timestamp": "2026-02-06T20:38:00Z"
}
```

### Job Status Tracking

Jobs progress through these stages:

1. **pending** (0%) - Job queued
2. **running** (10-90%) - Execution in progress
3. **completed** (100%) - Success
4. **failed** (0%) - Permanent failure
5. **retry** (0%) - Queued for retry

## 🧹 Database Maintenance

### Cleanup Job

Automated cleanup of old job records:

```bash
# Manual cleanup
curl -X DELETE "http://localhost:4000/api/v1/jobs/cleanup?days_to_keep=30"

# Background cleanup
curl -X DELETE "http://localhost:4000/api/v1/jobs/cleanup?days_to_keep=30&background=true"
```

### Cleanup Configuration

- **Default retention**: 30 days
- **Batch size**: 100 records per batch
- **Status filter**: Only completed/failed jobs
- **Background execution**: Available for large datasets

### Scheduled Cleanup

Add to your crontab for automated cleanup:

```bash
# Daily cleanup at 2 AM
0 2 * * * curl -X DELETE "http://localhost:4000/api/v1/jobs/cleanup?days_to_keep=30"
```

## 🚨 Production Considerations

### Security

1. **Environment Variables**: Never commit `.env.production` to version control
2. **Secrets Management**: Use secrets management service for production
3. **SSL/TLS**: Always use HTTPS in production
4. **Database Security**: Restrict database access to application servers
5. **Redis Security**: Enable authentication and restrict access

### Performance

1. **Database Indexes**: Ensure proper indexing on job tables
2. **Redis Configuration**: Optimize Redis for your workload
3. **Worker Scaling**: Scale Celery workers based on load
4. **Connection Pooling**: Configure appropriate database connection pools

### Monitoring

1. **Health Checks**: Monitor `/health` and `/ready` endpoints
2. **Job Queue**: Monitor pending job count
3. **Redis Metrics**: Monitor Redis memory and connection usage
4. **Error Tracking**: Set up error monitoring and alerting

### Backup & Recovery

1. **Database Backup**: Regular PostgreSQL backups
2. **Redis Backup**: Redis persistence configuration
3. **Configuration Backup**: Backup environment configurations
4. **Disaster Recovery**: Test recovery procedures

## 🐛 Troubleshooting

### Common Issues

#### Redis Unavailable

**Symptoms**: Jobs execute slowly, no Celery workers

**Solution**: 
- Check Redis connection
- Verify Redis configuration
- Monitor Redis logs
- Consider Redis clustering for high availability

#### Database Connection Issues

**Symptoms**: API errors, job failures

**Solution**:
- Check database connectivity
- Verify connection string
- Monitor database performance
- Check connection pool settings

#### Job Failures

**Symptoms**: Jobs stuck in failed state

**Solution**:
- Check job logs for error details
- Verify credit availability
- Check market data access
- Monitor system resources

### Debug Commands

```bash
# Check Redis status
redis-cli ping

# Check Celery status
celery -A app.celery_app.celery_app inspect ping

# Check job statistics
curl "http://localhost:4000/api/v1/system/status"

# Check specific job
curl "http://localhost:4000/api/v1/jobs/{job_id}"
```

## 📈 Scaling Guide

### Horizontal Scaling

1. **API Servers**: Scale API instances behind load balancer
2. **Celery Workers**: Add more worker instances
3. **Redis**: Consider Redis clustering
4. **Database**: Consider read replicas

### Load Balancer Configuration

```nginx
upstream api_servers {
    server api1:4000;
    server api2:4000;
    server api3:4000;
}

server {
    location / {
        proxy_pass http://api_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Worker Scaling

```bash
# Start multiple workers
celery -A app.celery_app.celery_app worker --concurrency 4 --loglevel=info

# Start workers on different queues
celery -A app.celery_app.celery_app worker --queues=backtest --loglevel=info
```

## 🔄 Deployment Checklist

### Pre-Deployment

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Redis configured and accessible
- [ ] SSL certificates configured
- [ ] Security headers configured
- [ ] Health check endpoints tested

### Post-Deployment

- [ ] Health checks passing
- [ ] Job execution tested
- [ ] Redis fallback tested
- [ ] Monitoring configured
- [ ] Backup procedures tested
- [ ] Documentation updated

### Production Validation

- [ ] Load testing completed
- [ ] Security scanning passed
- [ ] Performance benchmarks met
- [ ] Error handling tested
- [ ] Recovery procedures validated

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Review system logs
3. Monitor health check endpoints
4. Contact the development team with:
   - Environment details
   - Error messages
   - System status
   - Recent changes

---

**Last Updated**: February 2026
**Version**: 1.0.0
**Status**: Production Ready