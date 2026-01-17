from datetime import datetime, timezone
from enum import Enum
from typing import Optional, NamedTuple
from detector.config import ZOMBIE_THRESHOLD_DAYS
from detector.pypi_client import PyPIClient
from detector.github_client import GitHubClient


class HealthStatus(Enum):
    """Package health status."""
    SAFE = "SAFE"
    WARNING = "WARNING"
    UNKNOWN = "UNKNOWN"
    SKIPPED = "skipped"
    INVALID = "invalid"


class PackageHealth(NamedTuple):
    """Package health assessment result."""
    package_name: str
    status: HealthStatus
    github_url: Optional[str]
    last_commit_date: Optional[datetime]
    days_since_commit: Optional[int]
    reason: Optional[str] = None


class HealthChecker:
    """Check the health status of packages."""
    
    def __init__(self, pypi_client: Optional[PyPIClient] = None, 
                 github_client: Optional[GitHubClient] = None,
                 threshold_days: int = ZOMBIE_THRESHOLD_DAYS):
        self.pypi_client = pypi_client or PyPIClient()
        self.github_client = github_client or GitHubClient()
        self.threshold_days = threshold_days
        
    def validate_package(self, package_name: str) -> PackageHealth:
        """
        Validate if a package exists on PyPI (no GitHub checks)
        """
        exists, error_reason = self.pypi_client.package_exists(package_name)
        
        if exists:
            return PackageHealth(
                package_name=package_name,
                status=HealthStatus.SKIPPED,
                github_url=None,
                last_commit_date=None,
                days_since_commit=None,
                reason="Package exists on PyPI (validation mode)"
            )
        else:
            return PackageHealth(
                package_name=package_name,
                status=HealthStatus.INVALID,
                github_url=None,
                last_commit_date=None,
                days_since_commit=None,
                reason=error_reason or "Package not found on PyPI"
            )
         
    def check_package(self, package_name: str) -> PackageHealth:
        """
        Check if a package is alive or a zombie
        """
        # Get GitHub URL from PyPI
        github_url, error_reason = self.pypi_client.get_github_url(package_name)
        
        if not github_url:
            return PackageHealth(
                package_name=package_name,
                status=HealthStatus.UNKNOWN,
                github_url=None,
                last_commit_date=None,
                days_since_commit=None,
                reason=error_reason or "No GitHub repository found"
            )
        
        # Get last commit date from GitHub
        last_commit_date = self.github_client.get_last_commit_date(github_url)
        
        if not last_commit_date:
            return PackageHealth(
                package_name=package_name,
                status=HealthStatus.UNKNOWN,
                github_url=github_url,
                last_commit_date=None,
                days_since_commit=None,
                reason="Could not fetch repository data (404/Limit)"
            )
        
        # Calculate days since last commit
        now = datetime.now(timezone.utc)
        days_since = (now - last_commit_date).days
        
        # Determine status
        if days_since > self.threshold_days:
            status = HealthStatus.WARNING
            reason = f"No activity for {days_since} days (threshold: {self.threshold_days})"
        else:
            status = HealthStatus.SAFE
            reason = f"Active: last commit {days_since} days ago"
        
        return PackageHealth(
            package_name=package_name,
            status=status,
            github_url=github_url,
            last_commit_date=last_commit_date,
            days_since_commit=days_since,
            reason=reason
        )