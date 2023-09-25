"""ChangeType for restoring deleted items

Revision ID: 5e46d4ff6f21
Revises: 8a3f36ffa8df
Create Date: 2023-09-25 15:28:13.752183

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e46d4ff6f21'
down_revision = '8a3f36ffa8df'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE changetype ADD VALUE IF NOT EXISTS 'RESTORE'")


def downgrade():
    pass
