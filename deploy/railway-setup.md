# Railway Deployment Guide

This guide explains how to deploy the Travel Legal Alert System to Railway.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Push your code to GitHub
3. **Railway CLI** (optional): `npm install -g @railway/cli`

## Quick Deployment

### Method 1: Railway Dashboard (Recommended)

1. **Connect Repository**:
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

2. **Configure Environment**:
   - Railway will automatically detect the `railway.toml` configuration
   - Set the following environment variables in Railway dashboard:

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

3. **Add Database**:
   - In Railway dashboard, click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set `DATABASE_URL`

4. **Add Redis** (Optional):
   - In Railway dashboard, click "New" → "Database" → "Redis"
   - Railway will automatically set `REDIS_URL`

5. **Deploy**:
   - Railway will automatically build and deploy your application
   - Your app will be available at `https://your-app-name.up.railway.app`

### Method 2: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Link to existing project or create new one
railway link

# Set environment variables
railway variables set SECRET_KEY=your-super-secret-key
railway variables set JWT_SECRET_KEY=your-jwt-secret-key

# Add PostgreSQL database
railway add postgresql

# Add Redis (optional)
railway add redis

# Deploy
railway up
```

## Environment Variables

Railway automatically provides:
- `PORT` - Port number for the application
- `DATABASE_URL` - PostgreSQL connection string (if using Railway PostgreSQL)
- `REDIS_URL` - Redis connection string (if using Railway Redis)

### Required Environment Variables

Set these in Railway dashboard or CLI:

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
   railway run alembic upgrade head
   ```

3. **Seed Data**: To add sample data:
   ```bash
   railway run python scripts/seed_database.py
   ```

## Monitoring and Health Checks

- **Health Check**: `https://your-app.up.railway.app/health`
- **Metrics**: `https://your-app.up.railway.app/metrics` (Prometheus format)
- **API Docs**: `https://your-app.up.railway.app/docs`

## Custom Domain

1. In Railway dashboard, go to your project
2. Click "Settings" → "Domains"
3. Add your custom domain
4. Configure DNS records as instructed

## Scaling

Railway automatically handles:
- **Horizontal scaling** based on traffic
- **Auto-restart** on failures
- **Zero-downtime deployments**

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check Railway build logs
   - Ensure all dependencies are in `requirements.txt`
   - Verify Dockerfile is correct

2. **Database Connection Issues**:
   - Verify `DATABASE_URL` is set correctly
   - Check if database service is running
   - Ensure migrations have run

3. **Redis Connection Issues**:
   - Verify `REDIS_URL` is set correctly
   - Check if Redis service is running

4. **Health Check Failures**:
   - Check application logs
   - Verify health endpoint is responding
   - Ensure all dependencies are healthy

### Logs and Debugging

```bash
# View logs via CLI
railway logs

# Connect to running container
railway shell

# Run commands in container
railway run python scripts/seed_database.py
```

## Security Considerations

1. **Environment Variables**: Never commit secrets to Git
2. **HTTPS**: Railway provides HTTPS by default
3. **Security Headers**: Enabled by default in production
4. **Rate Limiting**: Configured and enabled
5. **CORS**: Configure for your frontend domains

## Cost Optimization

- **Free Tier**: Railway offers generous free tier
- **Usage Monitoring**: Monitor usage in Railway dashboard
- **Auto-scaling**: Configure appropriate scaling limits
- **Database**: Use appropriate database plan for your needs

## Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Railway Support**: Available in dashboard
