"""
Pydantic schemas for repository settings validation.

These schemas ensure that repository settings JSON is properly validated
before being stored in the database.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional


class RepositorySettings(BaseModel):
    """
    Repository-specific review configuration.

    Validates settings stored in Repository.settings JSON field.
    All settings have sane defaults.
    """

    auto_review_enabled: bool = Field(
        default=True,
        description="Enable automatic code reviews for this repository"
    )

    review_on_pr_open: bool = Field(
        default=True,
        description="Trigger review when a pull request is opened"
    )

    review_on_pr_update: bool = Field(
        default=True,
        description="Trigger review when a pull request is updated"
    )

    review_style: str = Field(
        default="detailed",
        description="Review style: 'detailed', 'concise', or 'security-focused'"
    )

    ignore_patterns: List[str] = Field(
        default_factory=lambda: ["*.md", "docs/*"],
        description="File patterns to ignore during review (glob format)"
    )

    max_files_per_review: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of files to review in a single PR (1-500)"
    )

    comment_style: str = Field(
        default="inline",
        description="How to post review comments: 'inline', 'summary', or 'both'"
    )

    min_severity_to_comment: str = Field(
        default="low",
        description="Minimum issue severity to post: 'low', 'medium', 'high', 'critical'"
    )

    enable_security_scanning: bool = Field(
        default=True,
        description="Enable security vulnerability detection"
    )

    enable_performance_checks: bool = Field(
        default=True,
        description="Enable performance and optimization suggestions"
    )

    enable_style_checks: bool = Field(
        default=False,
        description="Enable code style and formatting suggestions"
    )

    @validator('review_style')
    def validate_review_style(cls, v):
        """Validate review_style is one of allowed values."""
        allowed = ['detailed', 'concise', 'security-focused']
        if v not in allowed:
            raise ValueError(f"review_style must be one of {allowed}")
        return v

    @validator('comment_style')
    def validate_comment_style(cls, v):
        """Validate comment_style is one of allowed values."""
        allowed = ['inline', 'summary', 'both']
        if v not in allowed:
            raise ValueError(f"comment_style must be one of {allowed}")
        return v

    @validator('min_severity_to_comment')
    def validate_min_severity(cls, v):
        """Validate min_severity_to_comment is one of allowed values."""
        allowed = ['low', 'medium', 'high', 'critical']
        if v not in allowed:
            raise ValueError(f"min_severity_to_comment must be one of {allowed}")
        return v

    @validator('ignore_patterns')
    def validate_ignore_patterns(cls, v):
        """Ensure ignore_patterns is a list with reasonable length."""
        if len(v) > 100:
            raise ValueError("ignore_patterns cannot exceed 100 entries")
        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "auto_review_enabled": True,
                "review_on_pr_open": True,
                "review_on_pr_update": True,
                "review_style": "detailed",
                "ignore_patterns": ["*.md", "docs/*", "test/**"],
                "max_files_per_review": 50,
                "comment_style": "inline",
                "min_severity_to_comment": "medium",
                "enable_security_scanning": True,
                "enable_performance_checks": True,
                "enable_style_checks": False
            }
        }


def validate_repository_settings(settings_dict: dict) -> RepositorySettings:
    """
    Validate and parse repository settings from dict.

    Args:
        settings_dict: Raw settings dictionary from database

    Returns:
        Validated RepositorySettings instance

    Raises:
        ValidationError: If settings are invalid

    Example:
        >>> settings = validate_repository_settings(repo.settings)
        >>> if settings.auto_review_enabled:
        ...     trigger_review()
    """
    return RepositorySettings(**settings_dict)


def get_default_repository_settings() -> dict:
    """
    Get default repository settings as a dictionary.

    Use this when creating a new repository.

    Returns:
        Dictionary with default settings
    """
    return RepositorySettings().model_dump()
