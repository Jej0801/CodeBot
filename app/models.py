"""
Database models for CodeBot application.

All models inherit from Base (defined in app/database.py).
Models use async SQLAlchemy 2.0 patterns.
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime, JSON,
    Enum as SQLEnum, ForeignKey, Table, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
from app.core.encryption import encrypt_token, decrypt_token
from typing import Optional
import enum


# ----- Enums -----

class UserRole(str, enum.Enum):
    """
    Global application roles for users.

    Note: These are app-level roles, not repo-specific or org-specific.
    Future: May add separate models for org/repo-scoped permissions.

    Roles (least to most privilege):
    - VIEWER: Read-only access to reviews and comments
    - DEVELOPER: Can create review requests, view own data
    - REVIEWER: Can perform code reviews, comment on PRs
    - ADMIN: Can manage users, configure settings
    - OWNER: Full system access, typically for service administrators
    """
    VIEWER = "viewer"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    ADMIN = "admin"
    OWNER = "owner"


class RepositoryStatus(str, enum.Enum):
    """
    Repository monitoring status.

    Controls whether CodeBot actively monitors and reviews the repository.

    States:
    - ACTIVE: Normal operation, receiving webhooks and running reviews
    - PAUSED: Temporarily stopped, user/admin can resume
    - ARCHIVED: Repository archived on GitHub or in CodeBot, read-only
    - ERROR: Operational problem (permissions, sync failure, missing installation)
    """
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    ERROR = "error"


class SyncStatus(str, enum.Enum):
    """
    GitHub metadata synchronization status.

    Tracks the state of background sync jobs that update repository metadata
    from the GitHub API.

    States:
    - PENDING: Sync scheduled but not started
    - SYNCING: Currently fetching data from GitHub
    - SUCCESS: Last sync completed successfully
    - ERROR: Last sync failed (see sync_error for details)
    """
    PENDING = "pending"
    SYNCING = "syncing"
    SUCCESS = "success"
    ERROR = "error"


class RepositoryMemberRole(str, enum.Enum):
    """
    Repository-level access roles for users.

    Different from global UserRole - these are scoped to specific repositories.

    Roles:
    - VIEWER: Can view reviews and comments on this repo
    - CONTRIBUTOR: Can request reviews, view all reviews
    - MAINTAINER: Can configure repo settings, manage access
    - ADMIN: Full control over repo in CodeBot
    """
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    MAINTAINER = "maintainer"
    ADMIN = "admin"


# ----- Models -----

class User(Base):
    """
    User model for GitHub OAuth authentication and profile management.

    Security features:
    - GitHub OAuth tokens are encrypted at rest using Fernet (AES-128)
    - Tokens never appear in logs, repr, or API responses (use @property)
    - Soft delete support via deleted_at timestamp

    Authentication flow:
    1. User authenticates via GitHub OAuth
    2. GitHub returns access_token + refresh_token
    3. Tokens encrypted before storage
    4. Tokens decrypted on-demand for GitHub API calls

    Unique constraints:
    - github_id: One GitHub account = one CodeBot user
    - github_username: Enforces username uniqueness
    - email: One email per user (important for soft delete + re-registration)
    - api_token: Each user has unique API access token

    Soft delete behavior:
    - Setting deleted_at != NULL marks user as deleted
    - Unique constraints may conflict on re-registration
    - Historical reviews/comments preserved
    """
    __tablename__ = "users"

    # ----- Primary Key -----
    id = Column(Integer, primary_key=True, index=True)

    # ----- GitHub OAuth Fields -----
    github_id = Column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="GitHub user ID (immutable, used as external identifier)"
    )
    github_username = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="GitHub username (can change on GitHub, but unique in our system)"
    )

    # ENCRYPTED FIELDS - Do not access directly, use properties
    _github_access_token = Column(
        "github_access_token",
        String(500),
        nullable=True,
        comment="Encrypted GitHub OAuth access token (Fernet encrypted)"
    )
    _github_refresh_token = Column(
        "github_refresh_token",
        String(500),
        nullable=True,
        comment="Encrypted GitHub OAuth refresh token (Fernet encrypted)"
    )

    # ----- User Information -----
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email (from GitHub profile)"
    )
    display_name = Column(
        String(255),
        nullable=True,
        comment="Display name (GitHub name or custom)"
    )
    avatar_url = Column(
        String(500),
        nullable=True,
        comment="GitHub avatar URL"
    )
    bio = Column(
        Text,
        nullable=True,
        comment="User bio (from GitHub profile)"
    )
    github_profile_url = Column(
        String(500),
        nullable=True,
        comment="Link to GitHub profile"
    )

    # ----- Role & Permissions -----
    role = Column(
        SQLEnum(UserRole, name='user_roles', create_type=True),
        nullable=False,
        default=UserRole.DEVELOPER,
        comment="Global app role (not repo-specific). Default: developer"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Can user authenticate? Set to False to disable access"
    )
    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Has user verified their email? (future feature)"
    )

    # ----- CodeBot API Token -----
    api_token = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Token for programmatic API access (not encrypted, randomly generated)"
    )
    api_token_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="API token expiration timestamp"
    )

    # ----- User Preferences -----
    preferences = Column(
        JSON,
        default=dict,
        nullable=False,
        comment="User settings as JSON (notifications, review style, language, etc.)"
    )
    # Example preferences:
    # {
    #   "notifications": true,
    #   "review_style": "detailed",
    #   "language": "en",
    #   "theme": "dark"
    # }

    # ----- Timestamps -----
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="User registration timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last profile update timestamp"
    )
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful authentication timestamp"
    )

    # ----- Soft Delete -----
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft delete timestamp. NULL = active user, NOT NULL = deleted"
    )

    # ----- Relationships -----
    repository_memberships = relationship(
        "RepositoryMember",
        foreign_keys="RepositoryMember.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # reviews = relationship("Review", back_populates="created_by_user")
    # comments = relationship("Comment", back_populates="user")

    # ----- Properties for Token Access -----

    @property
    def github_access_token(self) -> Optional[str]:
        """
        Decrypt and return GitHub access token.

        Use this property to access the token for GitHub API calls.
        Never log or expose this value.

        Returns:
            Decrypted access token or None
        """
        if self._github_access_token:
            return decrypt_token(self._github_access_token)
        return None

    @github_access_token.setter
    def github_access_token(self, value: Optional[str]) -> None:
        """
        Encrypt and store GitHub access token.

        Args:
            value: Plaintext GitHub OAuth access token
        """
        self._github_access_token = encrypt_token(value) if value else None

    @property
    def github_refresh_token(self) -> Optional[str]:
        """
        Decrypt and return GitHub refresh token.

        Use this to refresh expired access tokens.

        Returns:
            Decrypted refresh token or None
        """
        if self._github_refresh_token:
            return decrypt_token(self._github_refresh_token)
        return None

    @github_refresh_token.setter
    def github_refresh_token(self, value: Optional[str]) -> None:
        """
        Encrypt and store GitHub refresh token.

        Args:
            value: Plaintext GitHub OAuth refresh token
        """
        self._github_refresh_token = encrypt_token(value) if value else None

    # ----- Utility Methods -----

    def is_deleted(self) -> bool:
        """
        Check if user is soft-deleted.

        Returns:
            True if deleted_at is set, False otherwise
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """
        Mark user as deleted without removing from database.

        Sets deleted_at to current timestamp.
        Historical data (reviews, comments) is preserved.
        """
        if not self.deleted_at:
            self.deleted_at = func.now()

    def restore(self) -> None:
        """
        Restore a soft-deleted user.

        Sets deleted_at back to None.
        """
        self.deleted_at = None

    def __repr__(self) -> str:
        """
        String representation for debugging.

        IMPORTANT: Does not include tokens for security reasons.
        """
        return (
            f"<User(id={self.id}, github_username='{self.github_username}', "
            f"email='{self.email}', role='{self.role.value}', "
            f"is_active={self.is_active}, deleted={self.is_deleted()})>"
        )


class RepositoryMember(Base):
    """
    Many-to-many association between Users and Repositories.

    Represents repository-level access control. A user can have access to
    multiple repositories, and a repository can have multiple users with
    different roles.

    This is separate from global UserRole - these roles are scoped to
    individual repositories.

    Use cases:
    - Track who can manage a repository's CodeBot settings
    - Control who can view private repository reviews
    - Audit who added/removed access
    - Support future organization/team features
    """
    __tablename__ = "repository_members"

    # ----- Primary Key -----
    id = Column(Integer, primary_key=True, index=True)

    # ----- Foreign Keys -----
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User with access to this repository"
    )
    repository_id = Column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Repository being accessed"
    )

    # ----- Access Control -----
    role = Column(
        SQLEnum(RepositoryMemberRole, name='repository_member_roles', create_type=True),
        nullable=False,
        default=RepositoryMemberRole.CONTRIBUTOR,
        comment="Repository-specific access role"
    )

    # ----- Audit Fields -----
    added_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When user was granted access"
    )
    added_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who granted this access"
    )

    # ----- Unique Constraint -----
    __table_args__ = (
        UniqueConstraint('user_id', 'repository_id', name='uq_user_repository'),
    )

    # ----- Relationships -----
    user = relationship("User", foreign_keys=[user_id], back_populates="repository_memberships")
    repository = relationship("Repository", back_populates="members")
    added_by = relationship("User", foreign_keys=[added_by_id])

    def __repr__(self) -> str:
        return (
            f"<RepositoryMember(user_id={self.user_id}, "
            f"repository_id={self.repository_id}, role='{self.role.value}')>"
        )


class Repository(Base):
    """
    GitHub repository being monitored for code reviews.

    Identity:
    - Primary stable identifier is github_repo_id (GitHub's immutable numeric ID)
    - owner/name/full_name are cached for convenience but can change on GitHub

    Access control:
    - Many-to-many relationship with User through RepositoryMember
    - Supports multiple users managing the same repository

    Lifecycle:
    - status controls active monitoring (active/paused/archived/error)
    - archived_at means repo no longer actively monitored
    - deleted_at means removed from CodeBot but history preserved

    Sync:
    - GitHub metadata cached and periodically refreshed
    - sync_status/sync_error track background sync job state
    """
    __tablename__ = "repositories"

    # ----- Primary Key -----
    id = Column(Integer, primary_key=True, index=True)

    # ----- GitHub Identification -----
    # github_repo_id is the STABLE identifier - use this for lookups
    github_repo_id = Column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="GitHub repository ID (immutable, stable identifier)"
    )

    # These fields can change if repo is renamed or transferred
    owner = Column(
        String(255),
        nullable=False,
        index=True,
        comment="GitHub owner/organization login (can change)"
    )
    name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Repository name (can change)"
    )
    full_name = Column(
        String(511),  # owner/name can be up to 255+255+1
        nullable=False,
        index=True,
        comment="Full repository name: 'owner/name' (can change)"
    )

    # ----- GitHub Metadata (Cached from API) -----
    is_private = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Is this a private repository?"
    )
    description = Column(
        Text,
        nullable=True,
        comment="Repository description from GitHub"
    )
    language = Column(
        String(100),
        nullable=True,
        comment="Primary programming language"
    )
    stargazers_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of GitHub stars (cached)"
    )
    forks_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of forks (cached)"
    )
    default_branch = Column(
        String(255),
        default="main",
        nullable=False,
        comment="Default branch name (main, master, etc.)"
    )
    html_url = Column(
        String(500),
        nullable=True,
        comment="GitHub repository URL"
    )

    # ----- Repository Status -----
    status = Column(
        SQLEnum(RepositoryStatus, name='repository_status', create_type=True),
        nullable=False,
        default=RepositoryStatus.ACTIVE,
        comment="Monitoring status (active, paused, archived, error)"
    )

    # ----- Repository Settings (Per-Repo Configuration) -----
    settings = Column(
        JSON,
        default=dict,
        nullable=False,
        comment="Per-repository review configuration (validated in app code)"
    )
    # Default settings structure:
    # {
    #   "auto_review_enabled": true,
    #   "review_on_pr_open": true,
    #   "review_on_pr_update": true,
    #   "review_style": "detailed",  # detailed, concise, security-focused
    #   "ignore_patterns": ["*.md", "docs/*", "test/**"],
    #   "max_files_per_review": 50,
    #   "comment_style": "inline"  # inline, summary, both
    # }

    # ----- GitHub Sync Tracking -----
    last_synced_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful metadata sync from GitHub"
    )
    sync_status = Column(
        SQLEnum(SyncStatus, name='sync_status', create_type=True),
        nullable=False,
        default=SyncStatus.PENDING,
        comment="Current sync job status"
    )
    sync_error = Column(
        Text,
        nullable=True,
        comment="Last sync error message (sanitized, bounded)"
    )

    # ----- Timestamps -----
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When repository was added to CodeBot"
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last metadata or settings update"
    )

    # ----- Archive & Soft Delete -----
    archived_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When repository was archived (stops active monitoring)"
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft delete timestamp. NULL = active, NOT NULL = deleted"
    )

    # ----- Relationships -----
    members = relationship(
        "RepositoryMember",
        back_populates="repository",
        cascade="all, delete-orphan"
    )
    # pull_requests = relationship("PullRequest", back_populates="repository")
    # reviews = relationship("Review", back_populates="repository")

    # ----- Utility Methods -----

    def is_active(self) -> bool:
        """Check if repository is actively monitored."""
        return (
            self.status == RepositoryStatus.ACTIVE and
            self.deleted_at is None and
            self.archived_at is None
        )

    def is_archived(self) -> bool:
        """Check if repository is archived."""
        return self.archived_at is not None

    def is_deleted(self) -> bool:
        """Check if repository is soft-deleted."""
        return self.deleted_at is not None

    def archive(self) -> None:
        """
        Archive repository (stops active monitoring).

        Different from deletion - archived repos remain visible but inactive.
        """
        if not self.archived_at:
            self.archived_at = func.now()
            self.status = RepositoryStatus.ARCHIVED

    def soft_delete(self) -> None:
        """
        Soft delete repository.

        Preserves historical reviews, PRs, and comments.
        Repository will be excluded from normal queries.
        """
        if not self.deleted_at:
            self.deleted_at = func.now()

    def restore(self) -> None:
        """Restore a soft-deleted repository."""
        self.deleted_at = None
        if self.status == RepositoryStatus.ARCHIVED and not self.archived_at:
            self.status = RepositoryStatus.ACTIVE

    def get_default_settings(self) -> dict:
        """
        Get default repository settings.

        Used when initializing a new repository or resetting settings.
        """
        return {
            "auto_review_enabled": True,
            "review_on_pr_open": True,
            "review_on_pr_update": True,
            "review_style": "detailed",
            "ignore_patterns": ["*.md", "docs/*"],
            "max_files_per_review": 50,
            "comment_style": "inline"
        }

    def __repr__(self) -> str:
        return (
            f"<Repository(id={self.id}, full_name='{self.full_name}', "
            f"github_repo_id={self.github_repo_id}, status='{self.status.value}', "
            f"is_private={self.is_private})>"
        )
