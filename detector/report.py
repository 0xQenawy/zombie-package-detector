from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from detector.health_checker import PackageHealth, HealthStatus


class Reporter:
    """Generate rich reports for package health checks."""
    
    def __init__(self):
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
        total = len(results)
        safe = sum(1 for r in results if r.status == HealthStatus.SAFE)
        warning = sum(1 for r in results if r.status == HealthStatus.WARNING)
        unknown = sum(1 for r in results if r.status == HealthStatus.UNKNOWN)
        
        summary_text = (
            f"[bold]Scanned:[/bold] {total} packages\n"
            f"[bold green]✓ SAFE:[/bold green] {safe}\n"
            f"[bold red]⚠ WARNING:[/bold red] {warning}\n"
            f"[bold yellow]? Unknown:[/bold yellow] {unknown}"
        )
        
        panel = Panel(
            summary_text,
            title="[bold]Scan Summary[/bold]",
            border_style="blue",
            expand=False
        )
        
        self.console.print()
        self.console.print(panel)
    
    def print_results_table(self, results: List[PackageHealth]):
        """Print detailed results in a table."""
        table = Table(title="Package Health Report", show_header=True, header_style="bold magenta")
        
        table.add_column("Package", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Days Since Commit", justify="right")
        table.add_column("GitHub URL", style="dim", overflow="fold")
        table.add_column("Details", overflow="fold")
        
        # Sort: Zombies first, then Alive, then Unknown
        status_order = {HealthStatus.WARNING: 0, HealthStatus.SAFE: 1, HealthStatus.UNKNOWN: 2}
        sorted_results = sorted(results, key=lambda r: (status_order[r.status], r.package_name))
        
        for result in sorted_results:
            if result.status == HealthStatus.WARNING:
                status_str = "WARNING"
                status_style = "bold red"
            elif result.status == HealthStatus.SAFE:
                status_str = "SAFE"
                status_style = "bold green"
            else:
                status_str = "Unknown"
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
    
    def print_error(self, message: str):
        """Print an error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")
    
    def print_warning(self, message: str):
        """Print a warning message."""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
    
    def print_info(self, message: str):
        """Print an info message."""
        self.console.print(f"[bold blue]Info:[/bold blue] {message}")