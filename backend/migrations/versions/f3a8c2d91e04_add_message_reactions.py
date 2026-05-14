"""add_message_reactions

Revision ID: f3a8c2d91e04
Revises: e61957fe1201
Create Date: 2026-03-25 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f3a8c2d91e04'
down_revision: Union[str, Sequence[str], None] = 'e61957fe1201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'message_reactions',
        sa.Column(
            'id',
            sa.UUID(),
            server_default=sa.text('uuid_generate_v4()'),
            nullable=False,
        ),
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('emoji', sa.String(length=64), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['message_id'], ['messages.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'message_id',
            'user_id',
            'emoji',
            name='uq_reaction_message_user_emoji',
        ),
    )
    op.create_index(
        'idx_reactions_message',
        'message_reactions',
        ['message_id'],
        unique=False,
    )
    op.execute(
        """
        CREATE TRIGGER update_message_reactions_updated_at
        BEFORE UPDATE ON message_reactions
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DROP TRIGGER IF EXISTS update_message_reactions_updated_at "
        "ON message_reactions"
    )
    op.drop_index('idx_reactions_message', table_name='message_reactions')
    op.drop_table('message_reactions')
