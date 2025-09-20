# Deployment Guide

This directory contains deployment configurations and guides for the Travel Legal Alert System.

## 🚀 Quick Start

Choose your deployment platform:

- **[Railway](railway-setup.md)** - Recommended for simplicity and developer experience
- **[Render](render-setup.md)** - Great for production with good free tier

## 📁 Files Overview

- `railway.toml` - Railway deployment configuration
- `render.yaml` - Render deployment configuration (Infrastructure as Code)
- `railway-setup.md` - Complete Railway deployment guide
- `render-setup.md` - Complete Render deployment guide

## 🏗️ Architecture Overview

The Travel Legal Alert System is designed with production-ready features:

### ✅ Production Features Implemented

1. **Environment-based Configuration** - Supports dev/staging/prod environments
2. **Structured Logging** - JSON logs with Sentry integration
3. **Health Checks** - Comprehensive health endpoints with dependency checks
4. **Metrics Collection** - Prometheus-compatible metrics
5. **Docker Optimization** - Multi-stage builds with security best practices
6. **Database Connection Pooling** - Optimized PostgreSQL connections
7. **Redis Configuration** - Caching and session management
8. **Security Headers** - CORS, rate limiting, CSRF protection

### 🏛️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│   FastAPI App   │────│   PostgreSQL    │
│   (Nginx)       │    │   (Gunicorn)    │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              │
                       ┌─────────────────┐
                       │     Redis       │
                       │   (Cache/Queue) │
                       └─────────────────┘
```

## 🔧 Pre-Deployment Checklist

### Required Environment Variables

```bash
# Security (REQUIRED - Generate secure keys)
SECRET_KEY=your-super-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Database (Auto-provided by platform)
DATABASE_URL=postgresql+asyncpg://...

# Redis (Auto-provided by platform, optional)
REDIS_URL=redis://...
```

### Optional Environment Variables

```bash
# External APIs
US_STATE_DEPT_API_KEY=your-api-key
UK_FOREIGN_OFFICE_API_KEY=your-api-key
NEWS_API_KEY=your-api-key

# Monitoring
SENTRY_DSN=your-sentry-dsn
SENTRY_ENVIRONMENT=production

# Feature Flags
ENABLE_SCRAPING=true
ENABLE_API_CLIENTS=true
ENABLE_NOTIFICATIONS=true
ENABLE_LOCATION_PROCESSING=true
```

## 🚀 Deployment Options

### Option 1: Railway (Recommended)

**Pros:**
- ✅ Excellent developer experience
- ✅ Automatic scaling
- ✅ Built-in PostgreSQL and Redis
- ✅ Zero-config deployments
- ✅ Generous free tier

**Cons:**
- ⚠️ Newer platform (less mature)
- ⚠️ Limited documentation

**Best for:** Development, staging, and small to medium production workloads

[**Deploy to Railway**](railway-setup.md)

### Option 2: Render

**Pros:**
- ✅ Mature platform with good documentation
- ✅ Infrastructure as Code support
- ✅ Good free tier
- ✅ Automatic HTTPS
- ✅ Built-in monitoring

**Cons:**
- ⚠️ Free tier has sleep limitations
- ⚠️ Less automatic scaling than Railway

**Best for:** Production applications, teams requiring Infrastructure as Code

[**Deploy to Render**](render-setup.md)

## 🔍 Health Monitoring

After deployment, verify your application is working:

### Health Endpoints

```bash
# Basic health check
curl https://your-app.com/health

# Readiness probe (Kubernetes compatible)
curl https://your-app.com/health/ready

# Liveness probe (Kubernetes compatible)
curl https://your-app.com/health/live

# Prometheus metrics
curl https://your-app.com/metrics
```

### Expected Health Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "response_time_ms": 45.2,
  "environment": "production",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12.3
    },
    "redis": {
      "status": "healthy", 
      "response_time_ms": 8.1
    }
  }
}
```

## 🛡️ Security Configuration

### Production Security Checklist

- [ ] Change default `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Set `DEBUG=false` in production
- [ ] Configure proper `CORS_ORIGINS` for your frontend
- [ ] Set up Sentry for error monitoring
- [ ] Configure rate limiting appropriately
- [ ] Enable security headers (`SECURITY_HEADERS_ENABLED=true`)
- [ ] Use HTTPS (automatic on both platforms)

### Security Headers

The application automatically includes:
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security` (HTTPS only)
- `Content-Security-Policy`
- `Permissions-Policy`

## 📊 Monitoring and Observability

### Metrics Available

- **HTTP Metrics**: Request counts, durations, status codes
- **Database Metrics**: Query performance, connection pool stats
- **Cache Metrics**: Hit ratios, operation durations
- **Business Metrics**: Scraping jobs, alerts sent, user activity
- **System Metrics**: Memory usage, CPU usage

### Logging

- **Structured Logging**: JSON format for easy parsing
- **Request Tracing**: Request IDs for correlation
- **Performance Logging**: Slow query detection
- **Security Logging**: Authentication and authorization events
- **Error Tracking**: Sentry integration for error monitoring

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Railway
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm install -g @railway/cli
      - run: railway up --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## 🆘 Troubleshooting

### Common Issues

1. **Build Failures**
   - Check platform build logs
   - Verify Dockerfile and dependencies
   - Ensure all required files are committed

2. **Database Connection Issues**
   - Verify `DATABASE_URL` is set correctly
   - Check database service is running
   - Ensure migrations have completed

3. **Health Check Failures**
   - Check application logs
   - Verify all dependencies are healthy
   - Test health endpoints manually

4. **Performance Issues**
   - Monitor resource usage
   - Check database query performance
   - Review cache hit ratios

### Getting Help

1. **Check Logs**: Use platform-specific log viewing tools
2. **Health Endpoints**: Test health and metrics endpoints
3. **Platform Support**: Use platform-specific support channels
4. **Application Logs**: Check structured application logs

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 🤝 Contributing

When adding new deployment configurations:

1. Follow the existing patterns in this directory
2. Include comprehensive documentation
3. Test configurations thoroughly
4. Update this README with new information
5. Consider security implications

---

**Need help?** Check the platform-specific guides or create an issue in the repository.
