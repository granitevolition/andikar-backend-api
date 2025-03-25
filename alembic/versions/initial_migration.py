"""Initial migration

Revision ID: 01c71591df2a
Revises: 
Create Date: 2025-03-25 11:37:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '01c71591df2a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('plan_id', sa.String(), nullable=False, server_default='free'),
        sa.Column('words_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payment_status', sa.String(), nullable=False, server_default='Pending'),
        sa.Column('joined_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('api_keys', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create pricing_plans table
    op.create_table('pricing_plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False, server_default='KES'),
        sa.Column('billing_cycle', sa.String(), nullable=False, server_default='monthly'),
        sa.Column('word_limit', sa.Integer(), nullable=False),
        sa.Column('requests_per_day', sa.Integer(), nullable=False),
        sa.Column('features', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pricing_plans_id'), 'pricing_plans', ['id'], unique=False)

    # Create transactions table
    op.create_table('transactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False, server_default='KES'),
        sa.Column('payment_method', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('transaction_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)

    # Create api_logs table
    op.create_table('api_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('request_size', sa.Integer(), nullable=False),
        sa.Column('response_size', sa.Integer(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_logs_id'), 'api_logs', ['id'], unique=False)

    # Create rate_limits table
    op.create_table('rate_limits',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('requests', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('last_updated', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rate_limits_id'), 'rate_limits', ['id'], unique=False)
    op.create_index(op.f('ix_rate_limits_key'), 'rate_limits', ['key'], unique=True)

    # Create webhooks table
    op.create_table('webhooks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('events', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('secret', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_triggered', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhooks_id'), 'webhooks', ['id'], unique=False)

    # Create usage_stats table
    op.create_table('usage_stats',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('day', sa.Integer(), nullable=False),
        sa.Column('humanize_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('detect_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('words_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_processing_time', sa.Float(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_stats_id'), 'usage_stats', ['id'], unique=False)

    # Insert default pricing plans
    op.execute("""
    INSERT INTO pricing_plans (id, name, description, price, word_limit, requests_per_day, features)
    VALUES
        ('free', 'Free Plan', 'Basic features for trying out the service', 0, 1000, 10, 
         '["Humanize text (limited)", "AI detection (limited)"]'::jsonb),
        ('basic', 'Basic Plan', 'Standard features for regular users', 999, 10000, 50, 
         '["Humanize text", "AI detection", "Email support"]'::jsonb),
        ('premium', 'Premium Plan', 'Advanced features for professional users', 2999, 50000, 100, 
         '["Humanize text", "AI detection", "Priority support", "API access"]'::jsonb)
    """)


def downgrade():
    op.drop_table('usage_stats')
    op.drop_table('webhooks')
    op.drop_table('rate_limits')
    op.drop_table('api_logs')
    op.drop_table('transactions')
    op.drop_table('pricing_plans')
    op.drop_table('users')
