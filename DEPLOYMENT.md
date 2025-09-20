# 🚀 Production Deployment Guide

This document provides a comprehensive guide for deploying the Travel Legal Alert System to production.

## 📋 Overview

The Travel Legal Alert System is a production-ready FastAPI application with comprehensive monitoring, security, and scalability features. All 8 production deployment requirements have been implemented:

✅ **Environment-based configuration**  
✅ **Structured logging with Sentry integration**  
✅ **Health check endpoints with dependency checks**  
✅ **Prometheus-compatible metrics collection**  
✅ **Optimized Docker configuration**  
✅ **Database connection pooling**  
✅ **Redis caching and session management**  
✅ **Security headers and CORS configuration**  

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│   FastAPI App   │────│   PostgreSQL    │
│   (Platform)    │    │   (Gunicorn)    │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              │
                       ┌─────────────────┐
                       │     Redis       │
                       │   (Cache/Queue) │
                       └─────────────────┘
```

## 🚀 Quick Deployment

### Option 1: Railway (Recommended)
```bash
# 1. Push code to GitHub
git push origin main

# 2. Connect to Railway
# - Go to railway.app
# - Connect GitHub repository
# - Railway will auto-detect railway.toml

# 3. Add services
# - Add PostgreSQL database
# - Add Redis (optional)
# - Set environment variables

# 4. Deploy
# - Railway auto-deploys on push
```

[**Detailed Railway Guide**](deploy/railway-setup.md)

### Option 2: Render
```bash
# 1. Push code to GitHub
git push origin main

# 2. Connect to Render
# - Go to render.com
# - Connect GitHub repository
# - Select render.yaml configuration

# 3. Deploy
# - Render auto-deploys on push
```

[**Detailed Render Guide**](deploy/render-setup.md)

## 🔧 Environment Configuration

### Required Environment Variables

```bash
# Security (CRITICAL - Generate secure keys)
SECRET_KEY=your-super-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Database (Auto-provided by platform)
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Redis (Auto-provided by platform)
REDIS_URL=redis://host:port/0
```

### Optional Environment Variables

```bash
# External API Keys
US_STATE_DEPT_API_KEY=your-api-key
UK_FOREIGN_OFFICE_API_KEY=your-api-key
NEWS_API_KEY=your-api-key

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production

# Feature Flags
ENABLE_SCRAPING=true
ENABLE_API_CLIENTS=true
ENABLE_NOTIFICATIONS=true
ENABLE_LOCATION_PROCESSING=true

# Performance Tuning
WORKERS=4
DB_POOL_SIZE=20
REDIS_POOL_SIZE=20
```

## 🛡️ Security Configuration

### Production Security Checklist

- [ ] **Change default secrets**: Update `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] **Disable debug mode**: Set `DEBUG=false`
- [ ] **Configure CORS**: Set appropriate `CORS_ORIGINS` for your frontend
- [ ] **Enable security headers**: `SECURITY_HEADERS_ENABLED=true`
- [ ] **Set up monitoring**: Configure Sentry DSN
- [ ] **Use HTTPS**: Automatic on both Railway and Render
- [ ] **Configure rate limiting**: Adjust `API_RATE_LIMIT_PER_MINUTE` as needed

### Security Features Implemented

- **Security Headers**: XSS protection, CSRF protection, content type validation
- **Rate Limiting**: Configurable per-endpoint rate limits with Redis backend
- **CORS Protection**: Environment-specific CORS configuration
- **Input Validation**: Comprehensive request validation
- **Authentication**: JWT-based authentication with secure token handling
- **Audit Logging**: Security events and access logging

## 📊 Monitoring and Health Checks

### Health Endpoints

```bash
# Comprehensive health check
GET /health
{
  "status": "healthy",
  "components": {
    "database": {"status": "healthy", "response_time_ms": 12.3},
    "redis": {"status": "healthy", "response_time_ms": 8.1},
    "external_apis": {"status": "healthy"}
  }
}

# Kubernetes readiness probe
GET /health/ready

# Kubernetes liveness probe  
GET /health/live

# Prometheus metrics
GET /metrics
```

### Monitoring Features

- **Structured Logging**: JSON logs with request tracing
- **Performance Metrics**: Request durations, database query times
- **Business Metrics**: User activity, alert delivery, scraping jobs
- **System Metrics**: Memory usage, CPU usage, connection pools
- **Error Tracking**: Sentry integration for error monitoring
- **Health Monitoring**: Comprehensive dependency health checks

## 🗄️ Database Setup

### Automatic Migration
The application automatically runs database migrations on startup in production:
```bash
AUTO_MIGRATE=true  # Default: true
```

### Manual Migration (if needed)
```bash
# Via platform shell/CLI
alembic upgrade head
```

### Seed Data (optional)
```bash
# Add sample data for testing
python scripts/seed_database.py
```

## 📈 Performance Optimization

### Database Optimization
- **Connection Pooling**: Configurable pool size and overflow
- **Query Optimization**: Automatic slow query detection and logging
- **Connection Monitoring**: Real-time pool statistics
- **Query Timeout**: Configurable statement timeouts

### Caching Strategy
- **Redis Caching**: Configurable TTL and cache strategies
- **Session Management**: Redis-based session storage
- **Rate Limiting**: Redis-backed distributed rate limiting
- **Background Tasks**: Celery with Redis broker

### Application Optimization
- **Gunicorn Workers**: Configurable worker count
- **Request Timeouts**: Configurable request and keep-alive timeouts
- **Memory Management**: Automatic worker recycling
- **Static File Serving**: Optimized static file handling

## 🔄 Scaling Configuration

### Horizontal Scaling
Both Railway and Render support automatic scaling:

**Railway:**
- Automatic scaling based on traffic
- Zero-config horizontal scaling
- Load balancing across instances

**Render:**
- Manual scaling via dashboard
- Auto-scaling with Pro plans
- Load balancing configuration

### Resource Limits
```yaml
# Example scaling configuration
scaling:
  minInstances: 1
  maxInstances: 10
  targetCPUUtilization: 70
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Build Failures
```bash
# Check platform build logs
# Verify Dockerfile and requirements.txt
# Ensure all files are committed to repository
```

#### 2. Database Connection Issues
```bash
# Verify DATABASE_URL format
# Check database service status
# Ensure migrations completed successfully
# Test connection manually
```

#### 3. Health Check Failures
```bash
# Check application logs
# Verify all dependencies are healthy
# Test health endpoints manually
# Check resource usage
```

#### 4. Performance Issues
```bash
# Monitor resource usage
# Check database query performance
# Review cache hit ratios
# Analyze request patterns
```

### Debug Commands

```bash
# Check application status
curl https://your-app.com/health

# View metrics
curl https://your-app.com/metrics

# Test database connection
# (via platform shell)
python -c "from app.core.database import engine; print(engine.url)"

# Test Redis connection
# (via platform shell)
python -c "from app.core.redis import redis_manager; print(redis_manager.health_check())"
```

## 📚 Platform-Specific Guides

### Railway
- **Pros**: Excellent DX, auto-scaling, zero-config
- **Cons**: Newer platform, limited docs
- **Best for**: Development, staging, small-medium production
- **[Railway Setup Guide](deploy/railway-setup.md)**

### Render
- **Pros**: Mature platform, IaC support, good docs
- **Cons**: Free tier limitations, manual scaling
- **Best for**: Production, teams needing IaC
- **[Render Setup Guide](deploy/render-setup.md)**

## 🔐 Security Best Practices

### Environment Security
1. **Never commit secrets** to version control
2. **Use platform secrets management** for sensitive data
3. **Rotate secrets regularly** in production
4. **Monitor access logs** for suspicious activity

### Application Security
1. **Enable all security headers** in production
2. **Configure appropriate CORS** origins
3. **Set up rate limiting** based on expected traffic
4. **Monitor security events** via logs and Sentry
5. **Keep dependencies updated** regularly

### Infrastructure Security
1. **Use HTTPS everywhere** (automatic on platforms)
2. **Configure proper firewall rules**
3. **Monitor resource usage** for anomalies
4. **Set up backup strategies** for critical data

## 📞 Support and Resources

### Getting Help
1. **Check platform documentation** first
2. **Review application logs** for errors
3. **Test health endpoints** to isolate issues
4. **Use platform support channels**

### Useful Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

## 🎉 Deployment Complete!

Your Travel Legal Alert System is now ready for production with:
- ✅ Comprehensive monitoring and health checks
- ✅ Production-grade security features
- ✅ Optimized performance and caching
- ✅ Scalable architecture
- ✅ Complete observability stack

**Next Steps:**
1. Configure your domain and SSL certificates
2. Set up monitoring alerts
3. Configure backup strategies
4. Set up CI/CD pipelines
5. Monitor application performance

**Need help?** Check the platform-specific guides or create an issue in the repository.
