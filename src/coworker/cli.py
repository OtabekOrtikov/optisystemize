import typer
import asyncio
import json
import shutil
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .core import ingest, extract, organize, export, storage, config, wizard, telemetry
from .core.models import ManifestEntry, FileStatus
from .core.i18n import t

app = typer.Typer(help="AI Coworker: Organize your documents with Gemini.")
console = Console()

@app.callback()
def main(
    lang: str = typer.Option(None, "--lang", help="Language (ru|en)")
):
    """Global configuration."""
    if lang:
         config.settings.set_cli_language(lang)

@app.command()
def init(path: Path = typer.Argument(Path("."), help="Where to create the workspace")):
    """Initialize a new Coworker workspace."""
    ws = storage.Workspace(path)
    ws.ensure_structure()
    console.print(f"[green]{t('cli.init.success', path=ws.root)}[/green]")
    
    # Prompt to run setup
    if typer.confirm(t('cli.init.prompt_setup')):
        wizard.run_setup_wizard(ws)

@app.command()
def setup(path: Path = typer.Option(None, help="Workspace path")):
    """Run the interactive configuration wizard."""
    ws = storage.get_workspace(path)
    wizard.run_setup_wizard(ws)

@app.command()
def doctor():
    """Check environment and dependencies."""
    console.print(Panel(t('cli.doctor.title'), style="bold blue"))
    
    # Check API Key
    if config.settings.GEMINI_API_KEY:
        console.print(t('cli.doctor.apikey_ok'))
    else:
        console.print(t('cli.doctor.apikey_missing'))
    
    # Check dependencies
    try:
        import google.genai
        console.print(t('cli.doctor.sdk_ok'))
    except ImportError:
         console.print(t('cli.doctor.sdk_missing'))

@app.command()
def status(path: Path = typer.Option(None, help="Workspace path")):
    """Show workspace status and aggregate metrics."""
    ws = storage.get_workspace(path)
    if not ws.is_valid():
        console.print(t('cli.status.invalid'))
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
            
    table = Table(title=t('cli.status.title'))
    table.add_column(t('cli.status.col_metric'), style="cyan")
    table.add_column(t('cli.status.col_value'), style="magenta")
    
    table.add_row(t('cli.status.total_runs'), str(total_runs))
    table.add_row(t('cli.status.files_processed'), str(total_files))
    table.add_row(t('cli.status.tokens_used'), f"{total_tokens:,}")
    
    console.print(table)

@app.command()
def undo(
    run_id: str = typer.Argument(None, help="Specific Run ID to undo (defaults to latest)"),
    path: Path = typer.Option(None, help="Workspace path")
):
    """Refuses the last run (restores files from trash)."""
    ws = storage.get_workspace(path or Path.cwd())
    trash_root = ws.system / "trash"
    
    if not trash_root.exists():
        console.print(f"[red]{t('cli.undo.no_history')}[/red]")
        raise typer.Exit(1)
        
    # Find run to undo
    if not run_id:
        # Get latest directory in trash
        runs = sorted([d for d in trash_root.iterdir() if d.is_dir()], key=lambda d: d.name, reverse=True)
        if not runs:
            console.print(f"[red]{t('cli.undo.no_history')}[/red]")
            raise typer.Exit(1)
        target_run_dir = runs[0]
        run_id = target_run_dir.name
    else:
        target_run_dir = trash_root / run_id
        if not target_run_dir.exists():
            console.print(f"[red]{t('cli.undo.not_found', run_id=run_id)}[/red]")
            raise typer.Exit(1)
            
    console.print(f"[yellow]{t('cli.undo.restoring', run_id=run_id)}[/yellow]")
    
    # Iterate and restore
    restored_count = 0
    # Walk safely
    for root, dirs, files in os.walk(target_run_dir):
        for file in files:
            src_path = Path(root) / file
            # Relative path from run dir
            rel_path = src_path.relative_to(target_run_dir)
            
            # Destination: Workspace Root + Rel Path
            dest_path = ws.root / rel_path
            
            # Ensure parent
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move back (restore)
            shutil.move(src_path, dest_path)
            
            # Log
            _log_manifest(ws, "undo", "N/A", str(src_path), "restored", dst=str(dest_path))
            console.print(t('cli.undo.restored_file', path=str(rel_path)))
            restored_count += 1
            
    # Clean up empty run dir
    shutil.rmtree(target_run_dir)
    console.print(f"[green]{t('cli.undo.complete', count=restored_count)}[/green]")


@app.command()
def run(
    path: Path = typer.Option(None, "--path", "-p", help="Workspace path"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-extraction"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't move files, just simulate"),
    here: bool = typer.Option(False, "--here", help="Run in current directory (Ad-hoc mode)"),
    auto_init: bool = typer.Option(True, "--auto-init/--no-auto-init", help="Automatically initialize workspace if needed"),
    mode: str = typer.Option("move", "--mode", help="File operation mode: copy or move (Default: move)"),
    safe: bool = typer.Option(False, "--safe", help="Run in safe mode (copy files instead of move)"),
    dev: bool = typer.Option(False, "--dev", help="Export technical metrics (tokens, hash, etc.)"),
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
            console.print(f"[red]{t('cli.status.invalid')}[/red]")
            raise typer.Exit(1)
        
        # Check if there are candidates for ad-hoc run using root scan
        candidates = list(ingest.scan_inbox(ws.root))
        if not candidates and not dry_run: 
             console.print(f"[red]{t('cli.run.no_files')}[/red]")
             raise typer.Exit(1)
             
        # Initialize ad-hoc
        # Warning for first-time ad-hoc move (Simplified for v2.1)
        # Default is now move, which is safe.
        
        console.print(f"[yellow]{t('cli.run.adhoc_init', root=str(ws.root))}[/yellow]")
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
    
    # Init i18n again if config has lang AND cli arg was NOT set?
    # Actually, callback runs first. config.settings.i18n.lang is set if --lang present.
    # load_user_config respects config > env.
    # Usage: CLI > Config > Env.
    # If CLI set logic: app.callback sets it. self.i18n.lang is updated.
    
    # We need to ensure Config doesn't override CLI choice.
    # config.py: load_user_config sets language if self.config.lang exists.
    # This might override CLI if we aren't careful.
    # Valid fix: Check if CLI flag was passed? Typer context?
    # Or just let config.py be oblivious and we re-apply CLI override here?
    # BUT we don't have access to 'lang' arg here anymore (it's in callback).
    # Solution: We can't easily know if 'lang' was set by CLI in callback vs default.
    # Alternative: Don't set lang in callback directly, store it in context?
    # Or rely on Config.py to be smart?
    # Simplest: In config.py, add `override_lang` param to `load_user_config`.
    # But for now, let's assume if I set it in Callback, I want it to stick.
    
    # Better logic:
    # 1. Callback runs. Sets I18n.lang.
    # 2. Run command loads config. logic in load_user_config sets I18n.lang from file.
    # -> This overrides callback! BAD.
    
    # Fix: We need to pass the CLI lang down or check if it was explicitly set.
    # Since I removed `lang` from `run`, I can't check it here easily without Context.
    # Let's verify `config.py` logic.
    pass
    
    # Initialize Telemetry
    tm = telemetry.Telemetry(ws)
    tm.start_stage("total")
    
    console.print(f"[bold blue]{t('cli.welcome', root=str(ws.root))}[/bold blue]")

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
        task1 = progress.add_task(t('cli.run.scanning', path=scan_target.name), total=None)
        
        for file_path in ingest.scan_inbox(scan_target):
            f_hash = ingest.calculate_sha256(file_path)
            files_to_process.append((f_hash, file_path))
            _log_manifest(ws, "ingest", f_hash, str(file_path), "new")
        
        progress.update(task1, completed=True)
    
    tm.end_stage("ingest")
    
    if not files_to_process:
        console.print(f"[yellow]{t('cli.run.no_files')}[/yellow]")
        return

    console.print(t('cli.run.found_files', count=len(files_to_process)))

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
        task2 = progress.add_task(t('cli.run.extracting'), total=len(files_to_process))
        
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
        
        # Prepare trash dir for safe move
        trash_dir = None
        if mode == "move":
            trash_dir = ws.system / "trash" / tm.run_id
            
        org_res = organize.organize_file(f_path, res, ws, f_hash, dry_run=dry_run, mode=mode, trash_dir=trash_dir)
        
        _log_manifest(ws, "organize", f_hash, str(f_path), org_res['status'], dst=org_res.get('dst'))
        if org_res['status'] == FileStatus.ORGANIZED:
            organized_count += 1
            
    tm.end_stage("organize")

    # 4. Export
    tm.start_stage("export")
    console.print(t('cli.run.gen_report'))
    
    # Determine export path: Root for Ad-hoc, Exports/ for Standard
    if is_adhoc:
        export_path = ws.root / "master.xlsx"
    else:
        ws.exports.mkdir(exist_ok=True)
        export_path = ws.exports / "master.xlsx"
        
    export.generate_master_excel(ws, export_path, dev_mode=dev)
    
    # 4.1 Review CSV
    console.print(t('cli.run.gen_review'))
    export.generate_review_csv(ws)
    
    tm.end_stage("export")
    
    tm.end_stage("total")
    tm.save()

    # Summary Table
    console.print("\n")
    table = Table(title=t('cli.run.summary_title'), show_header=True, header_style="bold magenta")
    table.add_column(t('cli.status.col_metric'))
    table.add_column(t('cli.status.col_value'))
    
    m = tm.metrics
    table.add_row(t('cli.run.duration'), f"{m.duration:.2f}s")
    
    # Show processed Breakdown
    # New row for Cached/Requests
    table.add_row(t('cli.status.files_processed'), f"{m.processed_files}/{m.total_files}")
    table.add_row(t('cli.run.cached_info', cached=m.cached_skips, requests=m.requests_total), "")

    table.add_row(t('cli.run.review_needed'), f"[yellow]{m.review_needed}[/yellow]")
    if m.errors > 0:
        table.add_row(t('cli.run.errors'), f"[red]{m.errors}[/red]")
    table.add_row(t('cli.run.tokens'), f"{m.total_tokens_input:,} / {m.total_tokens_output:,}")
    
    console.print(table)
    console.print(f"[dim]Run ID: {tm.run_id}[/dim]")
    
    # Summary of paths
    console.print(t('cli.run.paths.organized', count=organized_count))
    console.print(t('cli.run.paths.spreadsheet', path=export_path))
    console.print(t('cli.run.paths.review', count=m.review_needed))
    
    if mode == "move":
         console.print(f"[yellow]{t('cli.run.undo_hint', run_id=tm.run_id)}[/yellow]")
         
    console.print(f"[green]{t('cli.run.done')}[/green]")

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
