"""Add personality and phone setup fields

Revision ID: 009
Revises: 008
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Create enums
    lead_handling_preference_enum = postgresql.ENUM(
        'book_appointment', 'send_sms', 'take_message',
        name='lead_handling_preference_enum',
        create_type=False
    )
    lead_handling_preference_enum.create(op.get_bind(), checkfirst=True)
    
    phone_setup_type_enum = postgresql.ENUM(
        'purchased', 'forwarded',
        name='phone_setup_type_enum',
        create_type=False
    )
    phone_setup_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Add personality fields
    op.add_column('businesses', sa.Column('business_description', sa.Text(), nullable=True))
    op.add_column('businesses', sa.Column('services_and_prices', sa.Text(), nullable=True))
    op.add_column('businesses', sa.Column('lead_handling_preference', 
                                          sa.Enum('book_appointment', 'send_sms', 'take_message',
                                                  name='lead_handling_preference_enum'),
                                          nullable=True))
    op.add_column('businesses', sa.Column('custom_greeting', sa.Text(), nullable=True))
    op.add_column('businesses', sa.Column('system_prompt', sa.Text(), nullable=True))
    
    # Add phone setup tracking
    op.add_column('businesses', sa.Column('phone_setup_type',
                                          sa.Enum('purchased', 'forwarded',
                                                  name='phone_setup_type_enum'),
                                          nullable=True))


def downgrade():
    op.drop_column('businesses', 'phone_setup_type')
    op.drop_column('businesses', 'system_prompt')
    op.drop_column('businesses', 'custom_greeting')
    op.drop_column('businesses', 'lead_handling_preference')
    op.drop_column('businesses', 'services_and_prices')
    op.drop_column('businesses', 'business_description')
    
    # Drop enums
    sa.Enum(name='phone_setup_type_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='lead_handling_preference_enum').drop(op.get_bind(), checkfirst=True)
