"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-24 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import JSON
from app.models.code_chunk import PortableVector

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Repositories
    op.create_table(
        'repositories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('github_repo_id', sa.Integer(), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('owner', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('default_branch', sa.String(length=64), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False),
        sa.Column('is_demo', sa.Boolean(), nullable=False),
        sa.Column('indexed_commit_sha', sa.String(length=64), nullable=True),
        sa.Column('indexing_status', sa.String(length=32), nullable=False),
        sa.Column('indexing_progress', sa.Float(), nullable=False),
        sa.Column('indexing_error', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_repositories_full_name', 'repositories', ['full_name'], unique=True)
    op.create_index('ix_repositories_github_repo_id', 'repositories', ['github_repo_id'])

    # Repository Settings
    op.create_table(
        'repository_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('optional_ci_enabled', sa.Boolean(), nullable=False),
        sa.Column('auto_review_prs', sa.Boolean(), nullable=False),
        sa.Column('min_severity_to_alert', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repository_id')
    )

    # Code Chunks
    op.create_table(
        'code_chunks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('language', sa.String(length=64), nullable=False),
        sa.Column('symbol_name', sa.String(length=256), nullable=True),
        sa.Column('symbol_type', sa.String(length=64), nullable=True),
        sa.Column('start_line', sa.Integer(), nullable=False),
        sa.Column('end_line', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('embedding', PortableVector(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_code_chunks_commit_sha', 'code_chunks', ['commit_sha'])
    op.create_index('ix_code_chunks_content_hash', 'code_chunks', ['content_hash'])
    op.create_index('ix_code_chunks_file_path', 'code_chunks', ['file_path'])
    op.create_index('ix_code_chunks_repository_id', 'code_chunks', ['repository_id'])
    op.create_index('ix_code_chunks_symbol_name', 'code_chunks', ['symbol_name'])

    # Code Relationships
    op.create_table(
        'code_relationships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('source_file', sa.String(length=512), nullable=False),
        sa.Column('target_file', sa.String(length=512), nullable=True),
        sa.Column('relationship_type', sa.String(length=32), nullable=False),
        sa.Column('source_symbol', sa.String(length=256), nullable=False),
        sa.Column('target_symbol', sa.String(length=256), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('evidence_snippet', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_code_relationships_commit_sha', 'code_relationships', ['commit_sha'])
    op.create_index('ix_code_relationships_repository_id', 'code_relationships', ['repository_id'])
    op.create_index('ix_code_relationships_source_file', 'code_relationships', ['source_file'])

    # PR Reviews
    op.create_table(
        'pr_reviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('base_commit_sha', sa.String(length=64), nullable=False),
        sa.Column('head_commit_sha', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('ci_check_published', sa.Boolean(), nullable=False),
        sa.Column('ci_check_run_id', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pr_reviews_pr_number', 'pr_reviews', ['pr_number'])
    op.create_index('ix_pr_reviews_repository_id', 'pr_reviews', ['repository_id'])

    # Review Findings
    op.create_table(
        'review_findings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=False),
        sa.Column('end_line', sa.Integer(), nullable=False),
        sa.Column('why_problem', sa.Text(), nullable=False),
        sa.Column('suggested_improvement', sa.Text(), nullable=False),
        sa.Column('suggested_tests', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('is_confirmed_problem', sa.Boolean(), nullable=False),
        sa.Column('published_to_github', sa.Boolean(), nullable=False),
        sa.Column('github_comment_id', sa.String(length=64), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['pr_reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_review_findings_review_id', 'review_findings', ['review_id'])
    op.create_index('ix_review_findings_severity', 'review_findings', ['severity'])

    # Finding Feedback
    op.create_table(
        'finding_feedback',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('finding_id', sa.Integer(), nullable=False),
        sa.Column('is_useful', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('model_provider', sa.String(length=64), nullable=False),
        sa.Column('prompt_version', sa.String(length=32), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['finding_id'], ['review_findings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_finding_feedback_finding_id', 'finding_feedback', ['finding_id'])

    # Audit Log
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('action_type', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('repo_full_name', sa.String(length=255), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=True),
        sa.Column('target_file', sa.String(length=512), nullable=True),
        sa.Column('target_lines', sa.String(length=64), nullable=True),
        sa.Column('payload_summary', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_log_action_type', 'audit_log', ['action_type'])
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])
    op.create_index('ix_audit_log_repo_full_name', 'audit_log', ['repo_full_name'])


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('finding_feedback')
    op.drop_table('review_findings')
    op.drop_table('pr_reviews')
    op.drop_table('code_relationships')
    op.drop_table('code_chunks')
    op.drop_table('repository_settings')
    op.drop_table('repositories')
