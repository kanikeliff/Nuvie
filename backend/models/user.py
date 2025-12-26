"""
User model with comprehensive audit and security fields.

IMPROVEMENTS:
- Added is_active and is_verified flags for account status
- Added failed_login_attempts and locked_until for brute force protection
- Added last_login_at for activity tracking
- Added created_at and updated_at for audit trail
- Added proper SQLAlchemy type hints
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index
from sqlalchemy.sql import func

from backend.session import Base


class User(Base):
    """
    User model for authentication and authorization.

    Includes security features for brute force protection and
    audit fields for compliance tracking.
    """
    __tablename__ = "users"

    # Primary identification
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Security: Brute force protection
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Activity tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 max length

    # Audit trail
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Indexes for common queries
    __table_args__ = (
        Index('ix_users_email_active', 'email', 'is_active'),
        Index('ix_users_created_at', 'created_at'),
    )

    def is_locked(self) -> bool:
        """Check if the account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def increment_failed_login(self) -> int:
        """Increment failed login counter and return new count."""
        self.failed_login_attempts += 1
        return self.failed_login_attempts

    def reset_failed_logins(self) -> None:
        """Reset failed login counter after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_login(self, ip_address: Optional[str] = None) -> None:
        """Record successful login with timestamp and IP."""
        self.last_login_at = datetime.now(timezone.utc)
        if ip_address:
            self.last_login_ip = ip_address
        self.reset_failed_logins()

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"
