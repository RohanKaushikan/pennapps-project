-- Initial database setup script
-- This script runs when the PostgreSQL container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create additional schemas if needed
-- CREATE SCHEMA IF NOT EXISTS monitoring;
-- CREATE SCHEMA IF NOT EXISTS analytics;

-- Create indexes for common search patterns (will be created by migrations but good to have as backup)
-- These will be created automatically by SQLAlchemy migrations, but we can prepare them here

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE travel_alerts TO postgres;

-- Log the initialization
INSERT INTO information_schema.sql_features (feature_id, feature_name, sub_feature_id, sub_feature_name, is_supported, comments)
VALUES ('CUSTOM_001', 'Travel Alerts Database', '001', 'Initialized', 'YES', 'Database initialized at ' || NOW())
ON CONFLICT DO NOTHING;