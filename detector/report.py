import json
import sys
from typing import List
from rich.console import Console
from rich.table import Table, box
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from detector.health_checker import PackageHealth, HealthStatus

class Reporter:
    """Generate reports for package health checks in multiple formats."""
    
    def __init__(self, output_format: str = "table"):
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        self.output_format = output_format.lower().strip()
        if self.output_format == "json":
                self.console = Console(stderr=True)
        else:
                self.console = Console()
    
    def create_progress(self) -> Progress:
        """Create a progress bar for scanning packages."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
    
    def print_summary(self, results: List[PackageHealth]):
        """Print summary statistics."""
        if self.output_format in ["json", "markdown"]:
            return  
        
        total = len(results)
        safe = sum(1 for r in results if r.status == HealthStatus.SAFE)
        warning = sum(1 for r in results if r.status == HealthStatus.WARNING)
        unknown = sum(1 for r in results if r.status == HealthStatus.UNKNOWN)
        skipped = sum(1 for r in results if r.status == HealthStatus.SKIPPED)
        invalid = sum(1 for r in results if r.status == HealthStatus.INVALID)
        
        summary_text = f"[bold]Scanned:[/bold] {total} packages\n"
        
        if safe > 0:
            summary_text += f"[bold green] Safe:[/bold green] {safe}\n"
        if warning > 0:
            summary_text += f"[bold red] Warning:[/bold red] {warning}\n"
        if unknown > 0:
            summary_text += f"[bold yellow] Unknown:[/bold yellow] {unknown}\n"
        if skipped > 0:
            summary_text += f"[bold cyan] Skipped:[/bold cyan] {skipped}\n"
        if invalid > 0:
            summary_text += f"[bold red] Invalid:[/bold red] {invalid}"
        
        panel = Panel(
            summary_text.rstrip(),
            title="[bold]Scan Summary[/bold]",
            border_style="blue",
            expand=False
        )
        
        self.console.print()
        self.console.print(panel)
    
    def print_results(self, results: List[PackageHealth]):
        """Print results in the configured format."""
        if self.output_format == "json":
            self._print_json(results)
        elif self.output_format == "markdown":
            self._print_markdown(results)
        else:
            self._print_table(results)
    
    def _print_table(self, results: List[PackageHealth]):
        table = Table(
            title="Package Health Report",
            show_header=True,
            header_style="bold magenta",
            box=box.ASCII
        )
        
        table.add_column("Package", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Days Since Commit", justify="right")
        table.add_column("GitHub URL", style="dim", overflow="fold")
        table.add_column("Details", overflow="fold")
        
        status_order = {
            HealthStatus.WARNING: 0,
            HealthStatus.INVALID: 1,
            HealthStatus.SAFE: 2,
            HealthStatus.UNKNOWN: 3,
            HealthStatus.SKIPPED: 4
        }
        sorted_results = sorted(results, key=lambda r: (status_order[r.status], r.package_name))
        
        for result in sorted_results:
            if result.status == HealthStatus.WARNING:
                status_str = " WARNING"
                status_style = "bold red"
            elif result.status == HealthStatus.SAFE:
                status_str = " Safe"
                status_style = "bold green"
            elif result.status == HealthStatus.INVALID:
                status_str = " INVALID"
                status_style = "bold red"
            elif result.status == HealthStatus.SKIPPED:
                status_str = " Skipped"
                status_style = "bold cyan"
            else:
                status_str = " Unknown"
                status_style = "bold yellow"
            
            # Days since commit
            days_str = str(result.days_since_commit) if result.days_since_commit is not None else "-"
            
            # GitHub URL
            github_str = result.github_url if result.github_url else "N/A"
            
            # Details/Reason
            details = result.reason or "No information"
            
            table.add_row(
                result.package_name,
                f"[{status_style}]{status_str}[/{status_style}]",
                days_str,
                github_str,
                details
            )
        
        self.console.print()
        self.console.print(table)
    
    def _print_json(self, results: List[PackageHealth]):
        """Print results as JSON to stdout (CI-safe)."""
        output = {
            "version": "1.1.0",
            "total": len(results),
            "summary": {
                "safe": sum(1 for r in results if r.status == HealthStatus.SAFE),
                "warning": sum(1 for r in results if r.status == HealthStatus.WARNING),
                "unknown": sum(1 for r in results if r.status == HealthStatus.UNKNOWN),
                "skipped": sum(1 for r in results if r.status == HealthStatus.SKIPPED),
                "invalid": sum(1 for r in results if r.status == HealthStatus.INVALID)
            },
            "packages": []
        }
        
        for result in results:
            package_data = {
                "name": result.package_name,
                "status": result.status.value,
                "github_url": result.github_url,
                "days_since_commit": result.days_since_commit,
                "last_commit_date": result.last_commit_date.isoformat() if result.last_commit_date else None,
                "reason": result.reason
            }
            output["packages"].append(package_data)
        
        sys.stdout.write(json.dumps(output, indent=2))
        sys.stdout.write("\n")
        sys.stdout.flush()
    
    def _print_markdown(self, results: List[PackageHealth]):
        """Print results as GitHub-Flavored Markdown to stdout."""
        lines = []
        lines.append("# Package Health Report")
        lines.append("")
        
        # Summary
        total = len(results)
        safe = sum(1 for r in results if r.status == HealthStatus.SAFE)
        warning = sum(1 for r in results if r.status == HealthStatus.WARNING)
        unknown = sum(1 for r in results if r.status == HealthStatus.UNKNOWN)
        skipped = sum(1 for r in results if r.status == HealthStatus.SKIPPED)
        invalid = sum(1 for r in results if r.status == HealthStatus.INVALID)
        
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Packages**: {total}")
        if safe > 0:
            lines.append(f"-  **Safe**: {safe}")
        if warning > 0:
            lines.append(f"-  **Warning**: {warning}")
        if unknown > 0:
            lines.append(f"-  **Unknown**: {unknown}")
        if skipped > 0:
            lines.append(f"-  **Skipped**: {skipped}")
        if invalid > 0:
            lines.append(f"-  **Invalid**: {invalid}")
        
        lines.append("")
        lines.append("## Packages")
        lines.append("")
        lines.append("| Package | Status | Days Since Commit | GitHub URL | Details |")
        lines.append("|---------|--------|-------------------|------------|---------|")
        
        status_order = {
            HealthStatus.WARNING: 0,
            HealthStatus.INVALID: 1,
            HealthStatus.SAFE: 2,
            HealthStatus.UNKNOWN: 3,
            HealthStatus.SKIPPED: 4
        }
        sorted_results = sorted(results, key=lambda r: (status_order[r.status], r.package_name))
        
        for result in sorted_results:
            if result.status == HealthStatus.WARNING:
                status_str = " WARNING"
            elif result.status == HealthStatus.SAFE:
                status_str = " Safe"
            elif result.status == HealthStatus.INVALID:
                status_str = " INVALID"
            elif result.status == HealthStatus.SKIPPED:
                status_str = " Skipped"
            else:
                status_str = " Unknown"
            
            days_str = str(result.days_since_commit) if result.days_since_commit is not None else "-"
            github_str = result.github_url if result.github_url else "N/A"
            details =(result.reason or "No information").replace("\n", " ")
            
            lines.append(f"| {result.package_name} | {status_str} | {days_str} | {github_str} | {details} |")
        
        print("\n".join(lines), file=sys.stdout)
    
    def print_error(self, message: str):
        self.console.print(f"[bold red]Error:[/bold red] {message}")
    
    def print_warning(self, message: str):
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
    
    def print_info(self, message: str):
        self.console.print(f"[bold blue]Info:[/bold blue] {message}")