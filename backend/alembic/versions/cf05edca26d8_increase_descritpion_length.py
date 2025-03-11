"""increase_descritpion_length

Revision ID: cf05edca26d8
Revises: 5e46d4ff6f21
Create Date: 2025-03-11 08:17:06.550078

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'cf05edca26d8'
down_revision = '5e46d4ff6f21'
branch_labels = None
depends_on = None

# Assuming this is the correct table name and column
def upgrade():
    op.alter_column('attr_definitions', 'description',
                    existing_type=sa.String(128),
                    type_=sa.String(1000))

def downgrade():
    op.alter_column('attr_definitions', 'description',
                    existing_type=sa.String(128),
                    type_=sa.String(1000))