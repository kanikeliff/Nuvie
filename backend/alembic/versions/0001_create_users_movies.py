"""create users and movies tables

Revision ID: 0001_create_users_movies
Revises: 
Create Date: 2025-12-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_create_users_movies'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(), nullable=True),
    )

    op.create_table(
        'movies',
        sa.Column('movie_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('poster_url', sa.String(), nullable=True),
        sa.Column('overview', sa.String(), nullable=True),
        sa.Column('release_date', sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table('movies')
    op.drop_table('users')
