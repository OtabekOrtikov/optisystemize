import typer
import asyncio
import json
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .core import ingest, extract, organize, export, storage, config, wizard, telemetry
from .core.models import ManifestEntry, FileStatus

app = typer.Typer(help="AI Coworker: Organize your documents with Gemini.")
console = Console()

@app.command()
def init(path: Path = typer.Argument(Path("."), help="Where to create the workspace")):
    """Initialize a new Coworker workspace."""
    ws = storage.Workspace(path)
    ws.ensure_structure()
    console.print(f"[green]✅ Workspace initialized at: {ws.root}[/green]")
    
    # Prompt to run setup
    if typer.confirm("Do you want to configure settings now?"):
        wizard.run_setup_wizard(ws)

@app.command()
def setup(path: Path = typer.Option(None, help="Workspace path")):
    """Run the interactive configuration wizard."""
    ws = storage.get_workspace(path)
    wizard.run_setup_wizard(ws)

@app.command()
def doctor():
    """Check environment and dependencies."""
    console.print(Panel("🩺 Coworker Health Check", style="bold blue"))
    
    # Check API Key
    if config.settings.GEMINI_API_KEY:
        console.print("✅ [green]GEMINI_API_KEY found.[/green]")
    else:
        console.print("❌ [red]GEMINI_API_KEY is missing![/red] Set it in .env or environment variables.")
    
    # Check dependencies
    try:
        import google.genai
        console.print("✅ [green]Google GenAI SDK installed.[/green]")
    except ImportError:
         console.print("❌ [red]Google GenAI SDK missing.[/red]")

@app.command()
def status(path: Path = typer.Option(None, help="Workspace path")):
    """Show workspace status and aggregate metrics."""
    ws = storage.get_workspace(path)
    if not ws.is_valid():
        console.print("[red]Not a valid workspace.[/red]")
        raise typer.Exit(1)
        
    runs_dir = ws.system / "runs"
    total_runs = 0
    total_files = 0
    total_tokens = 0
    total_cost_est = 0.0 # Placeholder
    
    if runs_dir.exists():
        for run_file in runs_dir.glob("*.json"):
            try:
                with open(run_file) as f:
                    data = json.load(f)
                    total_runs += 1
                    total_files += data.get("processed_files", 0)
                    total_tokens += data.get("total_tokens_input", 0) + data.get("total_tokens_output", 0)
            except: pass
            
    table = Table(title="📊 Workspace Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Runs", str(total_runs))
    table.add_row("Files Processed", str(total_files))
    table.add_row("Total Tokens Used", f"{total_tokens:,}")
    
    console.print(table)


@app.command()
def run(
    path: Path = typer.Option(None, "--path", "-p", help="Workspace path"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-extraction"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't move files, just simulate"),
    here: bool = typer.Option(False, "--here", help="Run in current directory (Ad-hoc mode)"),
    auto_init: bool = typer.Option(True, "--auto-init/--no-auto-init", help="Automatically initialize workspace if needed"),
    mode: str = typer.Option("move", "--mode", help="File operation mode: copy or move (Default: move)"),
    safe: bool = typer.Option(False, "--safe", help="Run in safe mode (copy files instead of move)"),
    dev: bool = typer.Option(False, "--dev", help="Export technical metrics (tokens, hash, etc.)")
):
    """🚀 Run the full pipeline (Ingest -> Extract -> Organize -> Export)."""
    
    # Mode overrides
    if safe:
        mode = "copy"
    
    # Determine root path
    if path:
        root_path = path
    elif here:
        root_path = Path.cwd()
    else:
        root_path = Path.cwd()

    ws = storage.get_workspace(root_path)

    # Auto-Init & Ad-hoc Detection
    is_adhoc = False
    
    if ws.is_valid():
        # It is a workspace. Check if it's a "standard" one (has Inbox) or "ad-hoc" (flat).
        # We can detect standard by presence of Inbox dir or config entry? 
        # Actually persistence check based on Inbox existence is a good heuristic.
        if not ws.inbox.exists():
            # Workspace exists but no Inbox -> likely created via auto-init ad-hoc previously.
            is_adhoc = True
    else:
        # Not a workspace. Try auto-init?
        if not auto_init:
            console.print("[red]❌ Not a valid workspace and auto-init disabled. Please run 'coworker init'.[/red]")
            raise typer.Exit(1)
        
        # Check if there are candidates for ad-hoc run using root scan
        candidates = list(ingest.scan_inbox(ws.root))
        if not candidates and not dry_run: 
             console.print("[red]❌ Invalid workspace and no files found to process. Please run 'coworker init'.[/red]")
             raise typer.Exit(1)
             
        # Initialize ad-hoc
        # Warning for first-time ad-hoc move
        if mode == "move":
            console.print(Panel("[bold yellow]⚠️  First run: Default is MOVE[/bold yellow]\nOriginal files will be moved to 'Organized/'.\nUse [bold cyan]--safe[/bold cyan] or [bold cyan]--mode copy[/bold cyan] to keep originals.", title="Warning"))
            if not typer.confirm("Continue?", default=True):
                 raise typer.Exit(1)

        console.print(f"[yellow]⚠️  No workspace found, initializing Ad-hoc mode in: {ws.root}[/yellow]")
        ws.ensure_system_only()
        # Create output folders dynamically
        ws.organized.mkdir(exist_ok=True)
        ws.review.mkdir(exist_ok=True)
        # Exports dir is OPTIONAL in ad-hoc now, usually we just drop file in root
        if not is_adhoc:
             ws.exports.mkdir(exist_ok=True)
        is_adhoc = True

    # Load config
    # If ad-hoc and config doesn't exist, use defaults (which is totally fine)
    config.settings.load_user_config(ws.config_path)
    
    # Initialize Telemetry
    tm = telemetry.Telemetry(ws)
    tm.start_stage("total")
    
    console.print(f"[bold blue]🚀 Coworker v2.0 Running in: {ws.root}[/bold blue]")

    # 1. Ingest
    tm.start_stage("ingest")
    files_to_process = []
    
    # In Ad-hoc mode, inbox IS the root. In normal mode, it's Inbox/
    # However, if user runs `coworker run` inside a valid workspace root, 
    # we usually expect files in Inbox/. 
    # IF ad-hoc mode was triggered (is_adhoc=True), we scan root.
    # IF normal workspace, we scan Inbox/.
    
    scan_target = ws.root if is_adhoc else ws.inbox
    
    # Special case: If user explicitly used --here inside a workspace, maybe they want to scan root?
    # Logic: if folder has .coworker, it's a workspace. Standard flow expects Inbox.
    # If user wants to process files in root of a workspace, they should move them to Inbox.
    # So strictly: Workspace -> Scan path/Inbox. Ad-hoc -> Scan path.
    
    if not is_adhoc and not scan_target.exists():
         # Fallback for broken workspace structure
         scan_target.mkdir(exist_ok=True)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task1 = progress.add_task(f"Scanning {scan_target.name}...", total=None)
        
        for file_path in ingest.scan_inbox(scan_target):
            f_hash = ingest.calculate_sha256(file_path)
            files_to_process.append((f_hash, file_path))
            _log_manifest(ws, "ingest", f_hash, str(file_path), "new")
        
        progress.update(task1, completed=True)
    
    tm.end_stage("ingest")
    
    if not files_to_process:
        console.print("[yellow]⚠️ No files found to process.[/yellow]")
        return

    console.print(f"   Found {len(files_to_process)} files.")

    # 2. Extract
    tm.start_stage("extract")
    extractor = extract.Extractor()
    results = []
    
    async def process_batch():
        tasks = []
        for f_hash, f_path in files_to_process:
            cache_path = ws.cache / f"{f_hash}.json"
            tasks.append(extractor.extract_file(f_path, cache_path, force))
        return await asyncio.gather(*tasks)

    with Progress(
        SpinnerColumn(), 
        BarColumn(), 
        TextColumn("[progress.description]{task.description}"), 
        console=console
    ) as progress:
        task2 = progress.add_task("Extracting data (Gemini)...", total=len(files_to_process))
        
        # Determine batch size based on concurrency to update progress bar more smoothly?
        # Actually asyncio.gather waits for all. For better progress bar we'd need as_completed or manual semaphore handling in loop.
        # For simplicity, we just await all and update at end (or use a clever wrapper).
        # Let's stick to simple "wait" for now to avoid complexity bugs.
        results = asyncio.run(process_batch())
        progress.update(task2, completed=len(files_to_process))

    tm.end_stage("extract")

    # Log results & Update Telemetry
    for idx, res in enumerate(results):
        f_hash, f_path = files_to_process[idx]
        status = "extracted" if res else "error"
        _log_manifest(ws, "extract", f_hash, str(f_path), status)
        tm.log_file_processed(res, error=(res is None))

    # 3. Organize
    tm.start_stage("organize")
    organized_count = 0
    
    for idx, res in enumerate(results):
        if not res: continue
        f_hash, f_path = files_to_process[idx]
        
        org_res = organize.organize_file(f_path, res, ws, f_hash, dry_run=dry_run, mode=mode)
        
        _log_manifest(ws, "organize", f_hash, str(f_path), org_res['status'], dst=org_res.get('dst'))
        if org_res['status'] == FileStatus.ORGANIZED:
            organized_count += 1
            
    tm.end_stage("organize")

    # 4. Export
    tm.start_stage("export")
    console.print("4️⃣  Generating Master Report...")
    
    # Determine export path: Root for Ad-hoc, Exports/ for Standard
    if is_adhoc:
        export_path = ws.root / "master.xlsx"
    else:
        ws.exports.mkdir(exist_ok=True)
        export_path = ws.exports / "master.xlsx"
        
    export.generate_master_excel(ws, export_path, dev_mode=dev)
    tm.end_stage("export")
    
    tm.end_stage("total")
    tm.save()

    # Summary Table
    console.print("\n")
    table = Table(title="✨ Run Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Value")
    
    m = tm.metrics
    table.add_row("Total Duration", f"{m.duration:.2f}s")
    table.add_row("Files Processed", f"{m.processed_files}/{m.total_files}")
    table.add_row("Review Needed", f"[yellow]{m.review_needed}[/yellow]")
    if m.errors > 0:
        table.add_row("Errors", f"[red]{m.errors}[/red]")
    table.add_row("Tokens (In/Out)", f"{m.total_tokens_input:,} / {m.total_tokens_output:,}")
    
    console.print(table)
    console.print(f"[dim]Run ID: {tm.run_id}[/dim]")
    console.print(f"[green]Done! Check '{export_path}'[/green]")

def _log_manifest(ws, event, f_hash, src, status, dst=None):
    entry = ManifestEntry(
        event=event,
        hash=f_hash,
        src=src,
        status=status,
        dst=dst
    )
    with open(ws.manifest_path, "a") as f:
        f.write(entry.model_dump_json() + "\n")

if __name__ == "__main__":
    app()
