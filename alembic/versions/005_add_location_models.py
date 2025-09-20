"""Add location processing models

Revision ID: 005
Revises: 004
Create Date: 2024-09-20 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE locationeventtype AS ENUM ('country_entry', 'country_exit', 'geofence_enter', 'geofence_exit', 'emergency_area', 'border_crossing')")
    op.execute("CREATE TYPE alertseverity AS ENUM ('low', 'medium', 'high', 'critical')")
    op.execute("CREATE TYPE alerttype AS ENUM ('travel_advisory', 'safety_warning', 'emergency_alert', 'entry_requirements', 'health_advisory', 'weather_warning')")

    # Create location_events table
    op.create_table('location_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('device_id', sa.String(length=255), nullable=True),
        sa.Column('event_type', sa.Enum('country_entry', 'country_exit', 'geofence_enter', 'geofence_exit', 'emergency_area', 'border_crossing', name='locationeventtype'), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('accuracy_meters', sa.Float(), nullable=True),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('country_name', sa.String(length=255), nullable=False),
        sa.Column('region', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=255), nullable=True),
        sa.Column('previous_country_code', sa.String(length=3), nullable=True),
        sa.Column('previous_country_name', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_time_ms', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_location_events_user_id'), 'location_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_location_events_device_id'), 'location_events', ['device_id'], unique=False)
    op.create_index(op.f('ix_location_events_country_code'), 'location_events', ['country_code'], unique=False)

    # Create location_alerts table
    op.create_table('location_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('location_event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('alert_type', sa.Enum('travel_advisory', 'safety_warning', 'emergency_alert', 'entry_requirements', 'health_advisory', 'weather_warning', name='alerttype'), nullable=False),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', 'critical', name='alertseverity'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('country_name', sa.String(length=255), nullable=False),
        sa.Column('location_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('risk_level', sa.String(length=50), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('advisory_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('actions_required', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_location_alerts_location_event_id'), 'location_alerts', ['location_event_id'], unique=False)
    op.create_index(op.f('ix_location_alerts_user_id'), 'location_alerts', ['user_id'], unique=False)
    op.create_index(op.f('ix_location_alerts_country_code'), 'location_alerts', ['country_code'], unique=False)

    # Create geofence_zones table
    op.create_table('geofence_zones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('center_latitude', sa.Float(), nullable=False),
        sa.Column('center_longitude', sa.Float(), nullable=False),
        sa.Column('radius_meters', sa.Float(), nullable=False),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('zone_type', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('entry_alert_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('exit_alert_enabled', sa.Boolean(), nullable=True, default=False),
        sa.Column('alert_template', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_geofence_zones_country_code'), 'geofence_zones', ['country_code'], unique=False)

    # Create country_briefs table
    op.create_table('country_briefs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('country_name', sa.String(length=255), nullable=False),
        sa.Column('brief_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_sources', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=False, default='1.0'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_country_briefs_country_code'), 'country_briefs', ['country_code'], unique=False)

    # Create emergency_broadcasts table
    op.create_table('emergency_broadcasts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', 'critical', name='alertseverity'), nullable=False),
        sa.Column('alert_type', sa.Enum('travel_advisory', 'safety_warning', 'emergency_alert', 'entry_requirements', 'health_advisory', 'weather_warning', name='alerttype'), nullable=False),
        sa.Column('target_countries', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('target_regions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('radius_km', sa.Float(), nullable=True),
        sa.Column('issued_by', sa.String(length=255), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_recipients', sa.Float(), nullable=True, default=0),
        sa.Column('delivered_count', sa.Float(), nullable=True, default=0),
        sa.Column('read_count', sa.Float(), nullable=True, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table('emergency_broadcasts')
    op.drop_table('country_briefs')
    op.drop_table('geofence_zones')
    op.drop_table('location_alerts')
    op.drop_table('location_events')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS alerttype")
    op.execute("DROP TYPE IF EXISTS alertseverity")
    op.execute("DROP TYPE IF EXISTS locationeventtype")