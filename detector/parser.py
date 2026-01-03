from pathlib import Path
from typing import List
from packaging.requirements import Requirement, InvalidRequirement


def parse_requirements(filepath: Path) -> List[str]:
    """Parse requirements.txt and extract package names"""
    packages = []
    
    if not filepath.exists():
        raise FileNotFoundError(f"Requirements file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            if '#' in line:
                line = line.split('#')[0].strip()
            
            # Skip editable installs and URLs
            if line.startswith('-e') or line.startswith('http://') or line.startswith('https://'):
                continue
            
            # Skip other pip options
            if line.startswith('-'):
                continue
            
            try:
                req = Requirement(line)
                packages.append(req.name)
            except InvalidRequirement as e:
                print(f"Warning: Skipping invalid requirement on line {line_num}: {line} ({e})")
                continue
    
    # Return unique packages while preserving order
    return list(dict.fromkeys(packages))