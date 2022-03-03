"""AttrType Enum extension

Revision ID: 8a3f36ffa8df
Revises: ef9a7b3217c3
Create Date: 2022-02-28 10:54:10.999317

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a3f36ffa8df'
down_revision = 'ef9a7b3217c3'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE attrtype ADD VALUE 'DATE' AFTER 'DT'")


def downgrade():
    pass
