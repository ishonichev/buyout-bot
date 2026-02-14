"""Добавление полей cashback и cashback_amount, поддержка динамических товаров

Revision ID: 001_cashback
Revises: 
Create Date: 2026-02-14 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_cashback'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Применение миграции."""
    # Добавляем поле cashback в таблицу products
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cashback', sa.Float(), nullable=False, server_default='0.0'))
    
    # Добавляем поле cashback_amount в таблицу orders
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cashback_amount', sa.Float(), nullable=True))


def downgrade() -> None:
    """Откат изменений."""
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('cashback_amount')
    
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('cashback')
