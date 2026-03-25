"""add_group_chat_management

Revision ID: a1b2c3d4e5f6
Revises: f3a8c2d91e04
Create Date: 2026-03-25 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3a8c2d91e04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add group-specific columns to conversations
    op.add_column(
        'conversations', sa.Column('description', sa.Text(), nullable=True)
    )
    op.add_column(
        'conversations',
        sa.Column(
            'is_public', sa.Boolean(), server_default='false', nullable=False
        ),
    )
    op.add_column(
        'conversations',
        sa.Column(
            'max_participants',
            sa.Integer(),
            server_default='1000',
            nullable=False,
        ),
    )
    op.add_column(
        'conversations',
        sa.Column(
            'settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )

    # Create pinned_messages table
    op.create_table(
        'pinned_messages',
        sa.Column(
            'id',
            sa.UUID(),
            server_default=sa.text('uuid_generate_v4()'),
            nullable=False,
        ),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('pinned_by', sa.UUID(), nullable=True),
        sa.Column(
            'pinned_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['conversation_id'], ['conversations.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['message_id'], ['messages.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['pinned_by'], ['users.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'conversation_id', 'message_id', name='uq_pinned_conv_msg'
        ),
    )
    op.create_index(
        'idx_pinned_conversation',
        'pinned_messages',
        ['conversation_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_pinned_conversation', table_name='pinned_messages')
    op.drop_table('pinned_messages')
    op.drop_column('conversations', 'settings')
    op.drop_column('conversations', 'max_participants')
    op.drop_column('conversations', 'is_public')
    op.drop_column('conversations', 'description')
