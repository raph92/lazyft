"""Initial Migration

Revision ID: 53e77a272071
Revises: 
Create Date: 2022-02-02 15:21:25.038430

"""
from alembic import op
import sqlalchemy as sa
from sqlmodel import SQLModel  # NEW
import sqlmodel.sql.sqltypes  # NEW


# revision identifiers, used by Alembic.
revision = '53e77a272071'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###