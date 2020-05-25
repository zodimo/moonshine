"""test_new_branch

Revision ID: d6b3693634e8
Revises: 082c4b69bce1
Create Date: 2020-05-25 20:32:02.486600

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd6b3693634e8'
down_revision = '082c4b69bce1'
branch_labels = ('user_table',)
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
