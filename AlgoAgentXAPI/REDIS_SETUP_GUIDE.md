# Redis Setup Guide for AlgoAgentX

## Overview

Redis is failing to connect because the Redis server is not running on your system. This is expected behavior, and our fallback system is working correctly by using FastAPI BackgroundTasks instead.

## Option 1: Install and Run Redis (Recommended for Production)

### Windows Installation

1. **Download Redis for Windows:**
   - Go to: https://github.com/microsoftarchive/redis/releases
   - Download `Redis-x64-3.2.100.msi` (or latest version)

2. **Install Redis:**
   ```bash
   # Run the downloaded MSI installer
   # Follow the installation wizard
   # Make sure to check "Add Redis to PATH"
   ```

3. **Start Redis Server:**
   ```bash
   # Method 1: Using Windows Services
   # Open Services (services.msc) and start "Redis"
   
   # Method 2: Command Line
   redis-server.exe
   
   # Method 3: As Windows Service
   redis-server --service-install redis.windows.conf --loglevel verbose
   redis-server --service-start
   ```

4. **Verify Redis is Running:**
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

### Alternative: Using Docker (Recommended)

If you have Docker installed, this is the easiest method:

```bash
# Start Redis container
docker run -d -p 6379:6379 --name algoagentx-redis redis:alpine

# Verify Redis is running
docker ps
# Should show the redis container

# Test connection
docker exec algoagentx-redis redis-cli ping
# Should return: PONG
```

### Alternative: Using WSL (Windows Subsystem for Linux)

If you have WSL installed:

```bash
# Install Redis in WSL
sudo apt update
sudo apt install redis-server

# Start Redis
sudo service redis-server start

# Verify
redis-cli ping
# Should return: PONG
```

## Option 2: Use External Redis Service

### Redis Cloud (Free Tier)

1. Go to https://redis.com/try-free/
2. Sign up for a free account
3. Create a Redis database
4. Get connection details (host, port, password)
5. Update your `.env` file:

```bash
# Replace with your Redis Cloud details
REDIS_URL=redis://username:password@your-redis-host:port/0
# OR
REDIS_HOST=your-redis-host
REDIS_PORT=port
REDIS_DB=0
```

### Local Network Redis

If you have Redis running on another machine in your network:

```bash
# Update .env with the network Redis server details
REDIS_HOST=192.168.1.100  # Replace with actual IP
REDIS_PORT=6379
REDIS_DB=0
```

## Configuration Verification

### Check Current Configuration

```bash
# Check if Redis is accessible
telnet localhost 6379

# If telnet not available, use PowerShell
Test-NetConnection -ComputerName localhost -Port 6379
```

### Update Environment Variables

If Redis is running on a different port or requires authentication:

```bash
# .env file
REDIS_URL=redis://localhost:6380/0  # Different port
# OR with authentication
REDIS_URL=redis://username:password@localhost:6379/0

# OR individual components
REDIS_HOST=localhost
REDIS_PORT=6380  # Different port
REDIS_DB=0
REDIS_PASSWORD=your_password  # If authentication required
```

## Troubleshooting Common Issues

### Issue 1: Connection Refused (10061)

```bash
# Error: [Errno 10061] Connect call failed
# Solution: Redis server is not running
redis-server.exe  # Start Redis manually
# OR
# Check Windows Services and start Redis service
```

### Issue 2: Authentication Required

```bash
# Error: NOAUTH Authentication required
# Solution: Add password to configuration
REDIS_URL=redis://:password@localhost:6379/0
# OR
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password
```

### Issue 3: Port Already in Use

```bash
# Error: Address already in use
# Solution: Change Redis port or stop conflicting service
# Edit redis.conf and change port
port 6380  # Change from default 6379
```

### Issue 4: Firewall Blocking

```bash
# Windows Firewall may block Redis
# Allow Redis through Windows Firewall:
# 1. Open Windows Defender Firewall
# 2. Click "Allow an app through firewall"
# 3. Add redis-server.exe
```

## Testing Redis Connection

### Manual Test

```bash
# Test Redis connection manually
redis-cli ping
# Expected: PONG

# Test with authentication
redis-cli -a your_password ping
# Expected: PONG
```

### Python Test

```python
# Test Redis connection from Python
import redis

try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    result = r.ping()
    print(f"Redis connection successful: {result}")
except Exception as e:
    print(f"Redis connection failed: {e}")
```

## Production Recommendations

### 1. Use Redis Sentinel or Cluster

For production environments with high availability requirements:

```bash
# Redis Sentinel setup for high availability
# Redis Cluster setup for horizontal scaling
```

### 2. Enable Persistence

Ensure Redis data persistence is configured:

```bash
# In redis.conf
save 900 1      # Save if 1 key changed in 900 seconds
save 300 10     # Save if 10 keys changed in 300 seconds
save 60 10000   # Save if 10000 keys changed in 60 seconds

# Enable AOF (Append Only File)
appendonly yes
appendfsync everysec
```

### 3. Security Configuration

```bash
# Set Redis password
requirepass your_strong_password

# Bind to specific interface (not 0.0.0.0 in production)
bind 127.0.0.1

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command KEYS ""
```

## Development vs Production Configuration

### Development (Current Setup)

```bash
# Simple local Redis for development
REDIS_URL=redis://localhost:6379/0
# OR
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Production

```bash
# External Redis service with authentication
REDIS_URL=redis://username:password@redis.example.com:6379/0
# OR
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_production_password
```

## Next Steps

1. **Choose your Redis setup method** (Docker, Windows installer, or external service)
2. **Install and start Redis server**
3. **Verify connection with `redis-cli ping`**
4. **Restart your AlgoAgentX application**
5. **Check logs for successful Redis connection**

## Fallback System Status

Even if Redis is not available, your application will continue to work using FastAPI BackgroundTasks. The fallback system ensures:

- ✅ No application crashes
- ✅ Background job execution continues
- ✅ Job status tracking works normally
- ✅ All API endpoints remain functional

The only difference is that jobs will run synchronously in the background instead of using the more robust Redis/Celery queue system.