import sys
import argparse
from pathlib import Path
from detector.parser import parse_requirements
from detector.health_checker import HealthChecker ,HealthStatus
from detector.report import Reporter
from detector.config import GITHUB_TOKEN


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Detect unmaintained 'zombie' packages in your dependencies"
    )
    parser.add_argument(
        'requirements_file',
        type=Path,
        nargs='?',
        default=Path('requirements.txt'),
        help='Path to requirements.txt (default: requirements.txt)'
    )
    
    args = parser.parse_args()
    
    reporter = Reporter()
    
    # Check for GitHub token
    if not GITHUB_TOKEN:
        reporter.print_warning(
            "GITHUB_TOKEN not found in environment. "
            "API rate limits will be more restrictive (60 requests/hour)."
        )
        reporter.print_info(
            "Set GITHUB_TOKEN environment variable for higher rate limits (5000 requests/hour)."
        )
        reporter.console.print()
    
    # Parse requirements file
    try:
        reporter.print_info(f"Parsing {args.requirements_file}...")
        packages = parse_requirements(args.requirements_file)
        
        if not packages:
            reporter.print_warning("No packages found in requirements file.")
            return 0
        
        reporter.print_info(f"Found {len(packages)} package(s) to analyze.")
        reporter.console.print()
        
    except FileNotFoundError as e:
        reporter.print_error(str(e))
        return 1
    except Exception as e:
        reporter.print_error(f"Failed to parse requirements: {e}")
        return 1
    
    checker = HealthChecker()
    results = []
    
    # Scan packages with progress bar
    with reporter.create_progress() as progress:
        task = progress.add_task(
            "[cyan]Scanning packages...",
            total=len(packages)
        )
        
        for package in packages:
            progress.update(task, description=f"[cyan]Checking {package}...")
            health = checker.check_package(package)
            results.append(health)
            progress.advance(task)
  
    reporter.print_summary(results)
    reporter.print_results_table(results)
    
    # Exit with error code if zombies found
    zombie_count = sum(1 for r in results if r.status.value == HealthStatus.WARNING)
    return 1 if zombie_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())