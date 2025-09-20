# Render Deployment Guide

This guide explains how to deploy the Travel Legal Alert System to Render.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Push your code to GitHub
3. **GitHub Integration**: Connect your GitHub account to Render

## Quick Deployment

### Method 1: Render Dashboard (Recommended)

1. **Create New Web Service**:
   - Go to [render.com](https://render.com)
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select your repository

2. **Configure Build Settings**:
   - **Environment**: `Docker`
   - **Dockerfile Path**: `./Dockerfile`
   - **Docker Context**: `./`
   - **Start Command**: `scripts/entrypoint.sh web`

3. **Configure Environment Variables**:
   - In the "Environment" tab, add the following variables:

   ```bash
   # Required - Generate secure keys
   SECRET_KEY=your-super-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-key-here
   
   # Optional - External APIs
   US_STATE_DEPT_API_KEY=your-api-key
   UK_FOREIGN_OFFICE_API_KEY=your-api-key
   NEWS_API_KEY=your-api-key
   
   # Optional - Sentry monitoring
   SENTRY_DSN=your-sentry-dsn
   SENTRY_ENVIRONMENT=production
   ```

4. **Add Database**:
   - Click "New" → "PostgreSQL"
   - Choose plan (Starter is sufficient for development)
   - Note the connection details

5. **Add Redis** (Optional):
   - Click "New" → "Redis"
   - Choose plan (Starter is sufficient for development)
   - Note the connection details

6. **Deploy**:
   - Click "Create Web Service"
   - Render will build and deploy your application
   - Your app will be available at `https://your-app-name.onrender.com`

### Method 2: Using render.yaml (Infrastructure as Code)

1. **Commit render.yaml**:
   - The `deploy/render.yaml` file contains the complete configuration
   - Commit and push to your repository

2. **Deploy from YAML**:
   - In Render dashboard, click "New" → "Blueprint"
   - Connect your repository
   - Render will automatically detect and use `render.yaml`

## Environment Variables

Render automatically provides:
- `PORT` - Port number for the application
- `DATABASE_URL` - PostgreSQL connection string (if using Render PostgreSQL)
- `REDIS_URL` - Redis connection string (if using Render Redis)

### Required Environment Variables

Set these in Render dashboard:

```bash
SECRET_KEY=your-super-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
```

### Optional Environment Variables

```bash
# External API Keys
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

# Notification Services
NOTIFICATION_EMAIL_ENABLED=false
NOTIFICATION_SMS_ENABLED=false
NOTIFICATION_PUSH_ENABLED=true

# Email Configuration (if using email notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TLS=true

# SMS Configuration (if using SMS notifications)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_FROM_NUMBER=+1234567890
```

## Database Setup

1. **Automatic Migration**: The app will automatically run migrations on startup if `AUTO_MIGRATE=true` (default)

2. **Manual Migration**: If needed, you can run migrations manually:
   ```bash
   # In Render dashboard, go to your web service
   # Click "Shell" and run:
   alembic upgrade head
   ```

3. **Seed Data**: To add sample data:
   ```bash
   # In Render dashboard, go to your web service
   # Click "Shell" and run:
   python scripts/seed_database.py
   ```

## Background Workers

To run background tasks (Celery workers):

1. **Create Worker Service**:
   - Click "New" → "Background Worker"
   - Use the same Docker configuration
   - Set **Start Command**: `scripts/entrypoint.sh worker`

2. **Configure Environment**:
   - Use the same environment variables as your web service
   - Ensure `REDIS_URL` is set for Celery broker

## Monitoring and Health Checks

- **Health Check**: `https://your-app.onrender.com/health`
- **Metrics**: `https://your-app.onrender.com/metrics` (Prometheus format)
- **API Docs**: `https://your-app.onrender.com/docs`

## Custom Domain

1. In Render dashboard, go to your web service
2. Click "Settings" → "Custom Domains"
3. Add your custom domain
4. Configure DNS records as instructed by Render

## Scaling

Render provides:
- **Manual scaling** via dashboard
- **Auto-scaling** with Pro plans
- **Load balancing** across multiple instances

### Scaling Configuration

```yaml
# In render.yaml
scaling:
  minInstances: 1
  maxInstances: 10
```

## Plans and Pricing

### Free Tier Limitations
- **Sleep after 15 minutes** of inactivity
- **750 hours/month** of usage
- **Limited resources** (512MB RAM, 0.1 CPU)

### Paid Plans
- **Starter**: $7/month - Always on, 512MB RAM
- **Standard**: $25/month - 1GB RAM, better performance
- **Pro**: $85/month - 4GB RAM, auto-scaling

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check Render build logs
   - Ensure all dependencies are in `requirements.txt`
   - Verify Dockerfile is correct

2. **Service Sleep Issues**:
   - Free tier services sleep after inactivity
   - Use paid plans for always-on services
   - Consider using external monitoring to keep service alive

3. **Database Connection Issues**:
   - Verify `DATABASE_URL` is set correctly
   - Check if database service is running
   - Ensure migrations have run

4. **Redis Connection Issues**:
   - Verify `REDIS_URL` is set correctly
   - Check if Redis service is running

5. **Health Check Failures**:
   - Check application logs
   - Verify health endpoint is responding
   - Ensure all dependencies are healthy

### Logs and Debugging

1. **View Logs**:
   - Go to your service in Render dashboard
   - Click "Logs" tab
   - View real-time and historical logs

2. **Shell Access**:
   - Go to your service in Render dashboard
   - Click "Shell" tab
   - Run commands directly in the container

3. **Debug Mode**:
   ```bash
   # Set in environment variables
   DEBUG=true
   LOG_LEVEL=DEBUG
   ```

## Security Considerations

1. **Environment Variables**: Never commit secrets to Git
2. **HTTPS**: Render provides HTTPS by default
3. **Security Headers**: Enabled by default in production
4. **Rate Limiting**: Configured and enabled
5. **CORS**: Configure for your frontend domains

## Performance Optimization

1. **Resource Limits**: Choose appropriate plan for your needs
2. **Caching**: Redis caching is configured and enabled
3. **Database Optimization**: Connection pooling is configured
4. **Static Files**: Use CDN for static assets if needed

## Backup and Recovery

1. **Database Backups**: Render provides automated backups for paid plans
2. **Manual Backups**: Use pg_dump for manual backups
3. **Environment Variables**: Export and backup your environment configuration

## Support

- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Render Status**: [status.render.com](https://status.render.com)
- **Render Support**: Available in dashboard or via email
- **Community**: [Render Community Forum](https://community.render.com)

## Migration from Other Platforms

### From Heroku
1. Export environment variables from Heroku
2. Set up databases in Render
3. Update `DATABASE_URL` and `REDIS_URL`
4. Deploy to Render

### From Railway
1. Export environment variables from Railway
2. Set up databases in Render
3. Update connection strings
4. Deploy to Render
