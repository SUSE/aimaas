"""Initial

Revision ID: fc081d95dc62
Revises: 
Create Date: 2021-11-30 15:51:21.706796

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc081d95dc62'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('attributes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('type', sa.Enum('STR', 'BOOL', 'INT', 'FLOAT', 'FK', 'DT', name='attrtype'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'type')
    )
    op.create_index(op.f('ix_attributes_id'), 'attributes', ['id'], unique=False)
    op.create_table('schemas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('slug', sa.String(length=128), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_schemas_id'), 'schemas', ['id'], unique=False)
    op.create_table('attr_definitions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('schema_id', sa.Integer(), nullable=True),
    sa.Column('attribute_id', sa.Integer(), nullable=True),
    sa.Column('required', sa.Boolean(), nullable=True),
    sa.Column('unique', sa.Boolean(), nullable=True),
    sa.Column('key', sa.Boolean(), nullable=True),
    sa.Column('list', sa.Boolean(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ),
    sa.ForeignKeyConstraint(['schema_id'], ['schemas.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('schema_id', 'attribute_id')
    )
    op.create_index(op.f('ix_attr_definitions_id'), 'attr_definitions', ['id'], unique=False)
    op.create_table('entities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('slug', sa.String(length=128), nullable=False),
    sa.Column('schema_id', sa.Integer(), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['schema_id'], ['schemas.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug', 'schema_id')
    )
    op.create_index(op.f('ix_entities_id'), 'entities', ['id'], unique=False)
    op.create_table('bound_foreign_keys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('attr_def_id', sa.Integer(), nullable=True),
    sa.Column('schema_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['attr_def_id'], ['attr_definitions.id'], ),
    sa.ForeignKeyConstraint(['schema_id'], ['schemas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bound_foreign_keys_id'), 'bound_foreign_keys', ['id'], unique=False)
    op.create_table('values_bool',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Boolean(), nullable=True),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('attribute_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_values_bool_id'), 'values_bool', ['id'], unique=False)
    op.create_table('values_datetime',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('value', sa.DateTime(timezone=True), nullable=True),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('attribute_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_values_datetime_id'), 'values_datetime', ['id'], unique=False)
    op.create_table('values_fk',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=True),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('attribute_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_values_fk_id'), 'values_fk', ['id'], unique=False)
    op.create_table('values_float',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Float(), nullable=True),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('attribute_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_values_float_id'), 'values_float', ['id'], unique=False)
    op.create_table('values_int',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=True),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('attribute_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_values_int_id'), 'values_int', ['id'], unique=False)
    op.create_table('values_str',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('value', sa.String(), nullable=True),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('attribute_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_values_str_id'), 'values_str', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_values_str_id'), table_name='values_str')
    op.drop_table('values_str')
    op.drop_index(op.f('ix_values_int_id'), table_name='values_int')
    op.drop_table('values_int')
    op.drop_index(op.f('ix_values_float_id'), table_name='values_float')
    op.drop_table('values_float')
    op.drop_index(op.f('ix_values_fk_id'), table_name='values_fk')
    op.drop_table('values_fk')
    op.drop_index(op.f('ix_values_datetime_id'), table_name='values_datetime')
    op.drop_table('values_datetime')
    op.drop_index(op.f('ix_values_bool_id'), table_name='values_bool')
    op.drop_table('values_bool')
    op.drop_index(op.f('ix_bound_foreign_keys_id'), table_name='bound_foreign_keys')
    op.drop_table('bound_foreign_keys')
    op.drop_index(op.f('ix_entities_id'), table_name='entities')
    op.drop_table('entities')
    op.drop_index(op.f('ix_attr_definitions_id'), table_name='attr_definitions')
    op.drop_table('attr_definitions')
    op.drop_index(op.f('ix_schemas_id'), table_name='schemas')
    op.drop_table('schemas')
    op.drop_index(op.f('ix_attributes_id'), table_name='attributes')
    op.drop_table('attributes')
    # ### end Alembic commands ###
