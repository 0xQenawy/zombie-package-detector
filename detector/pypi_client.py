import requests
from typing import Optional
from urllib.parse import urlparse
from detector.config import PYPI_API_URL, GITHUB_PATTERNS, PRIORITY_LABELS, IGNORE_LABELS


class PyPIClient:
    """Client for interacting with PyPI JSON API."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Zombie-Package-Detector/1.0'
        })
        
        
    def package_exists(self, package_name: str) -> tuple[bool, Optional[str]]:
        """Check if a package exists on PyPI."""
        try:
            url = PYPI_API_URL.format(package=package_name)
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 404:
                return False, "Package not found on PyPI"
            
            response.raise_for_status()
            return True, None
            
        except requests.exceptions.Timeout:
            return False, "PyPI API timeout"
        except requests.exceptions.ConnectionError:
            return False, "PyPI API connection error"
        except requests.exceptions.RequestException as e:
            return False, f"PyPI API error: {str(e)}"
    
    def get_github_url(self, package_name: str) -> Optional[str]:
        
        """Resolve GitHub URL from PyPI metadata, prioritizing source code links over docs"""
        try:
            url = PYPI_API_URL.format(package=package_name)
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 404:
                return None, "Package not found on PyPI"
            
            response.raise_for_status()
            data = response.json()
            
            info = data.get('info', {})
            
            # Collect all potential URLs
            github_urls = {}
            
            # Check project_urls
            project_urls = info.get('project_urls') or {}
            for label, url in project_urls.items():
                if url and self._is_github_url(url):
                    # Normalize label for comparison
                    label_lower = label.lower()
                    
                    # Skip documentation and tracker URLs
                    if any(ignore in label_lower for ignore in IGNORE_LABELS):
                        continue
                    
                    github_urls[label] = url
            
            # Check home_page
            home_page = info.get('home_page')
            if home_page and self._is_github_url(home_page):
                github_urls['home_page'] = home_page
            
            if not github_urls:
                return None, "No GitHub repository found in PyPI metadata"
            
            # First, look for priority labels
            for label, url in github_urls.items():
                label_lower = label.lower()
                if any(priority in label_lower for priority in PRIORITY_LABELS):
                    return self._normalize_github_url(url), None
            
            # If no priority label found, return the first GitHub URL
            return self._normalize_github_url(next(iter(github_urls.values()))), None
            
        except requests.exceptions.Timeout:
            return None, "PyPI API timeout"
        except requests.exceptions.ConnectionError:
            return None, "PyPI API connection error"
        except requests.exceptions.RequestException as e:
            return None, f"PyPI API error: {str(e)}"
        except (KeyError, ValueError) as e:
            return None, f"Error parsing PyPI data: {str(e)}"
    
    def _is_github_url(self, url: str) -> bool:
        """Check if URL is a GitHub repository URL."""
        if not url:
            return False
        
        try:
            parsed = urlparse(url.lower())
            return any(pattern in parsed.netloc for pattern in GITHUB_PATTERNS)
        except Exception:
            return False
    
    def _normalize_github_url(self, url: str) -> str:
        """
        Normalize GitHub URL to standard format.
        
        Example: https://github.com/user/repo.git -> https://github.com/user/repo
        """
        url = url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        return url