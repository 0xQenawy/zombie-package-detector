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
                 github_client: Optional[GitHubClient] = None):
        self.pypi_client = pypi_client or PyPIClient()
        self.github_client = github_client or GitHubClient()
    
    def check_package(self, package_name: str) -> PackageHealth:
        """
        Check if a package is alive or a zombie
        """
        # Step 1: Get GitHub URL from PyPI
        github_url = self.pypi_client.get_github_url(package_name)
        
        if not github_url:
            return PackageHealth(
                package_name=package_name,
                status=HealthStatus.UNKNOWN,
                github_url=None,
                last_commit_date=None,
                days_since_commit=None,
                reason="No GitHub repository found"
            )
        
        # Step 2: Get last commit date from GitHub
        last_commit_date = self.github_client.get_last_commit_date(github_url)
        
        if not last_commit_date:
            return PackageHealth(
                package_name=package_name,
                status=HealthStatus.UNKNOWN,
                github_url=github_url,
                last_commit_date=None,
                days_since_commit=None,
                reason="Could not fetch repository data"
            )
        
        # Step 3: Calculate days since last commit
        now = datetime.now(timezone.utc)
        days_since = (now - last_commit_date).days
        
        # Step 4: Determine status
        if days_since > ZOMBIE_THRESHOLD_DAYS:
            status = HealthStatus.WARNING
            reason = f"No activity for {days_since} days (threshold: {ZOMBIE_THRESHOLD_DAYS})"
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