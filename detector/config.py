import os
from pathlib import Path
from typing import Optional

GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")


ZOMBIE_THRESHOLD_DAYS = 730  
CACHE_DIR = Path.home() / ".cache" / "zombie-detector"
CACHE_FILE = CACHE_DIR / "github_cache.json"
PYPI_API_URL = "https://pypi.org/pypi/{package}/json"
GITHUB_API_URL = "https://api.github.com/repos/{owner}/{repo}"
GITHUB_PATTERNS = ["github.com"]
PRIORITY_LABELS = ["source", "code", "repository", "repo"]
IGNORE_LABELS = ["documentation", "docs", "tracker", "issues", "bug"]

CACHE_DIR.mkdir(parents=True, exist_ok=True)