import json
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from urllib.parse import urlparse
from detector.config import GITHUB_TOKEN, GITHUB_API_URL, CACHE_FILE


class GitHubClient:
    """Client for interacting with GitHub API with caching."""
    
    def __init__(self, token: Optional[str] = None, cache_file: Path = CACHE_FILE):
        self.token = token or GITHUB_TOKEN
        self.cache_file = cache_file
        self.session = requests.Session()
        
        # Set up headers
        self.session.headers.update({
            'User-Agent': 'Zombie-Package-Detector/1.0',
            'Accept': 'application/vnd.github.v3+json'
        })
        
        if self.token:
            self.session.headers['Authorization'] = f'token {self.token}'
        
        # Load cache
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load cache: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cache: {e}")
    
    def _get_cache_key(self, github_url: str) -> str:
        """Generate cache key from GitHub URL."""
        return hashlib.sha256(github_url.encode()).hexdigest()
    
    def _parse_github_url(self, github_url: str) -> Optional[tuple]:
        
        """Extract owner and repo from GitHub URL"""
        
        try:
            parsed = urlparse(github_url)
            path_parts = [p for p in parsed.path.split('/') if p]
            
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]
            
            return None
        except Exception:
            return None
    
    def get_repo_info(self, github_url: str) -> Optional[Dict[str, Any]]:
        """Fetch repository information from GitHub API"""
        cache_key = self._get_cache_key(github_url)
        
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            cached_at_str = cached_data.get('cached_at')
            if cached_at_str:
                try:
                    cached_at = datetime.fromisoformat(cached_at_str)
                    if datetime.utcnow() - cached_at < timedelta(hours=24):
                            return {
                                'pushed_at': cached_data.get('pushed_at'),
                                'from_cache': True
                            }
                except ValueError:
                    pass
        
        # Parse GitHub URL
        parsed = self._parse_github_url(github_url)
        if not parsed:
            print(f"Warning: Could not parse GitHub URL: {github_url}")
            return None
        
        owner, repo = parsed
        
        try:
            url = GITHUB_API_URL.format(owner=owner, repo=repo)
            response = self.session.get(url, timeout=10)
            
            # Handle rate limiting
            if response.status_code == 403:
                rate_limit = response.headers.get('X-RateLimit-Remaining', 'unknown')
                print(f"Warning: GitHub API rate limit exceeded (remaining: {rate_limit})")
                return None
            
            # Handle not found
            if response.status_code == 404:
                print(f"Warning: Repository not found: {owner}/{repo}")
                return None
            
            response.raise_for_status()
            data = response.json()
            repo_info = {
                'pushed_at': data.get('pushed_at'),
                'from_cache': False
            }
            
            # Cache the result
            self.cache[cache_key] = {
                'pushed_at': repo_info['pushed_at'],
                'cached_at': datetime.utcnow().isoformat(),
                'url': github_url
            }
            self._save_cache()
            
            return repo_info
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching GitHub data for {github_url}: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"Error parsing GitHub data for {github_url}: {e}")
            return None
    
    def get_last_commit_date(self, github_url: str) -> Optional[datetime]:
        
        """Get the date of the last commit (pushed_at)"""
        
        repo_info = self.get_repo_info(github_url)
        if not repo_info or not repo_info.get('pushed_at'):
            return None
        
        try:
            return datetime.fromisoformat(repo_info['pushed_at'].replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            print(f"Error parsing date for {github_url}: {e}")
            return None