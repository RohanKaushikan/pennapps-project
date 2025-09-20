"""Add reactive alerting system

Revision ID: 006
Revises: 005_add_location_models
Create Date: 2024-09-20 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005_add_location_models'
branch_labels = None
depends_on = None


def upgrade():
    """Add UserCountryEntry table for reactive alerting."""
    
    # Create user_country_entries table
    op.create_table('user_country_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('country_code', sa.String(length=2), nullable=False),
        sa.Column('entry_latitude', sa.Float(), nullable=True),
        sa.Column('entry_longitude', sa.Float(), nullable=True),
        sa.Column('entry_accuracy', sa.Float(), nullable=True),
        sa.Column('entry_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('alerts_sent', sa.Boolean(), nullable=False),
        sa.Column('alerts_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_user_country_entries_user_id', 'user_country_entries', ['user_id'])
    op.create_index('ix_user_country_entries_country_code', 'user_country_entries', ['country_code'])
    op.create_index('ix_user_country_entries_entry_timestamp', 'user_country_entries', ['entry_timestamp'])
    op.create_index('ix_user_country_entries_exit_timestamp', 'user_country_entries', ['exit_timestamp'])

    # Add comment to table
    op.execute("COMMENT ON TABLE user_country_entries IS 'Track when users enter new countries for reactive alerting'")
    op.execute("COMMENT ON COLUMN user_country_entries.country_code IS 'ISO 3166-1 alpha-2 country code'")
    op.execute("COMMENT ON COLUMN user_country_entries.entry_latitude IS 'GPS latitude when entering country'")
    op.execute("COMMENT ON COLUMN user_country_entries.entry_longitude IS 'GPS longitude when entering country'")
    op.execute("COMMENT ON COLUMN user_country_entries.entry_accuracy IS 'GPS accuracy in meters'")
    op.execute("COMMENT ON COLUMN user_country_entries.entry_timestamp IS 'When user entered the country'")
    op.execute("COMMENT ON COLUMN user_country_entries.alerts_sent IS 'Whether alerts have been sent for this entry'")
    op.execute("COMMENT ON COLUMN user_country_entries.alerts_sent_at IS 'When alerts were sent'")
    op.execute("COMMENT ON COLUMN user_country_entries.exit_timestamp IS 'When user left the country (if tracked)'")


def downgrade():
    """Remove UserCountryEntry table."""
    
    # Drop indexes
    op.drop_index('ix_user_country_entries_exit_timestamp', table_name='user_country_entries')
    op.drop_index('ix_user_country_entries_entry_timestamp', table_name='user_country_entries')
    op.drop_index('ix_user_country_entries_country_code', table_name='user_country_entries')
    op.drop_index('ix_user_country_entries_user_id', table_name='user_country_entries')
    
    # Drop table
    op.drop_table('user_country_entries')
