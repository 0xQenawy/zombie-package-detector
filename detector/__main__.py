import sys
import argparse
from pathlib import Path
from detector.parser import parse_requirements
from detector.health_checker import HealthChecker ,HealthStatus
from detector.report import Reporter
from detector.config import GITHUB_TOKEN, ZOMBIE_THRESHOLD_DAYS


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Detect unmaintained 'zombie' packages in your dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'requirements_file',
        type=Path,
        nargs='?',
        default=Path('requirements.txt'),
        help='Path to requirements.txt (default: requirements.txt)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=ZOMBIE_THRESHOLD_DAYS,
        help=f'Inactivity threshold in days (default: {ZOMBIE_THRESHOLD_DAYS})'
    )
    parser.add_argument(
        '--format',
        choices=['table', 'json', 'markdown'],
        default='table',
        help='Output format (default: table)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validation mode: only check if packages exist on PyPI (skip GitHub checks)'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching of GitHub API responses'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.1.0'
    )
    
    args = parser.parse_args()
    
    reporter = Reporter(output_format=args.format)
    
    
    if not args.validate and not GITHUB_TOKEN and args.format == 'table':
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
        if args.format == 'table':
            reporter.print_info(f"Parsing {args.requirements_file}...")
        
        packages = parse_requirements(args.requirements_file)
        
        if not packages:
            if args.format == 'table':
                reporter.print_warning("No packages found in requirements file.")
            return 0
        
        if args.format == 'table':
            reporter.print_info(f"Found {len(packages)} package(s) to analyze.")
            reporter.console.print()
        
    except FileNotFoundError as e:
        reporter.print_error(str(e))
        return 1
    except Exception as e:
        reporter.print_error(f"Failed to parse requirements: {e}")
        return 1
    
    # Initialize health checker with custom threshold
    checker = HealthChecker(threshold_days=args.days)
    results = []
    
    # Scan packages with progress bar (only for table format)
    if args.format == 'table':
        with reporter.create_progress() as progress:
            task = progress.add_task(
                "[cyan]Scanning packages...",
                total=len(packages)
            )
            
            for package in packages:
                progress.update(task, description=f"[cyan]Checking {package}...")
                
                if args.validate:
                    health = checker.validate_package(package)
                else:
                    health = checker.check_package(package)
                
                results.append(health)
                progress.advance(task)
    else:
        # Silent scanning for JSON/Markdown output
        for package in packages:
            if args.validate:
                health = checker.validate_package(package)
            else:
                health = checker.check_package(package)
            results.append(health)
    
    reporter.print_summary(results)
    reporter.print_results(results)
    has_warning = any(r.status == HealthStatus.WARNING for r in results)
    has_invalid = any(r.status == HealthStatus.INVALID for r in results)
    
    return 1 if (has_warning or has_invalid) else 0


if __name__ == "__main__":
    sys.exit(main())