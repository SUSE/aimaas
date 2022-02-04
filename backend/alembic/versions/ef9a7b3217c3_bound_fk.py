"""Bound FK

Revision ID: ef9a7b3217c3
Revises: 5e7b010c57b8
Create Date: 2022-02-04 08:55:06.006728

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ef9a7b3217c3'
down_revision = '5e7b010c57b8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_bound_foreign_keys_id', table_name='bound_foreign_keys')
    op.drop_table('bound_foreign_keys')
    op.add_column('attr_definitions', sa.Column('bound_schema_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'attr_definitions', 'schemas', ['bound_schema_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'attr_definitions', type_='foreignkey')
    op.drop_column('attr_definitions', 'bound_schema_id')
    op.create_table('bound_foreign_keys',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('attr_def_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('schema_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['attr_def_id'], ['attr_definitions.id'], name='bound_foreign_keys_attr_def_id_fkey'),
    sa.ForeignKeyConstraint(['schema_id'], ['schemas.id'], name='bound_foreign_keys_schema_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='bound_foreign_keys_pkey')
    )
    op.create_index('ix_bound_foreign_keys_id', 'bound_foreign_keys', ['id'], unique=False)
    # ### end Alembic commands ###
