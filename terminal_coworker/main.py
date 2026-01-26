import typer
from pathlib import Path
from datetime import datetime
import json
import os
from typing import Optional

from terminal_coworker.utils import calculate_sha256
from terminal_coworker.core import extract, organize, export
from terminal_coworker.models import ManifestEntry

app = typer.Typer()

def append_manifest(project_path: Path, entry: dict):
    with open(project_path / "manifest.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# --- ИСПРАВЛЕНИЕ: Добавили typer.Argument для путей и typer.Option для флагов ---

@app.command()
def init(
    project_path: Path = typer.Argument(..., help="Where to create the project")
):
    """Create project structure."""
    dirs = ["inbox", "files", "cache", "outputs"]
    for d in dirs:
        (project_path / d).mkdir(parents=True, exist_ok=True)
    
    manifest = project_path / "manifest.jsonl"
    if not manifest.exists():
        manifest.touch()
        
    typer.echo(f"Initialized project at {project_path}")

@app.command()
def ingest(
    inbox_path: Path = typer.Argument(..., help="Folder with source files"),
    project_path: Path = typer.Option(..., "--project-path", "-p", help="Project folder")
):
    """Scan inbox and hash files."""
    count = 0
    if not inbox_path.exists():
        typer.echo(f"Error: Inbox {inbox_path} not found.")
        raise typer.Exit(code=1)

    for root, _, files in os.walk(inbox_path):
        for name in files:
            file_path = Path(root) / name
            if name.startswith('.'): continue 
            
            f_hash = calculate_sha256(file_path)
            
            entry = ManifestEntry(
                ts=datetime.utcnow().isoformat(),
                event="ingest",
                hash=f_hash,
                src=str(file_path.absolute()), # Лучше сохранять абсолютный путь
                kind="file",
                status="new"
            )
            append_manifest(project_path, entry.model_dump())
            count += 1
    typer.echo(f"Ingested {count} files.")

@app.command()
def extract_cmd(
    project_path: Path = typer.Option(..., "--project-path", "-p"),
    force: bool = typer.Option(False, "--force", "-f")
):
    """Run AI extraction on ingested files."""
    files_to_process = {}
    
    # Читаем манифест, чтобы найти файлы
    manifest_path = project_path / "manifest.jsonl"
    if not manifest_path.exists():
         typer.echo("Manifest not found. Run init first.")
         raise typer.Exit(1)

    with open(manifest_path, "r") as f:
        for line in f:
            try:
                d = json.loads(line)
                if d['event'] == 'ingest':
                    files_to_process[d['hash']] = Path(d['src'])
            except json.JSONDecodeError:
                continue

    typer.echo(f"Found {len(files_to_process)} unique files in manifest.")
    
    for f_hash, src_path in files_to_process.items():
        if not src_path.exists():
            typer.echo(f"Skipping missing file: {src_path}")
            continue
            
        typer.echo(f"Processing: {src_path.name}")
        result = extract.extract_data(src_path, f_hash, project_path, force)
        
        status = "extracted" if result else "error"
        
        append_manifest(project_path, {
            "ts": datetime.utcnow().isoformat(),
            "event": "extract",
            "hash": f_hash,
            "src": str(src_path),
            "kind": "image" if src_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp'] else "other",
            "status": status
        })

@app.command()
def organize_cmd(
    project_path: Path = typer.Option(..., "--project-path", "-p"),
    mode: str = typer.Option("copy", help="copy or move"),
    dry_run: bool = typer.Option(False, "--dry-run")
):
    """Sort files based on cache data (Handles Duplicates)."""
    import shutil # Убедись, что импортирован shutil
    
    # 1. Читаем манифест и собираем все файлы, которые мы "заинжестили"
    ingested_files = []
    with open(project_path / "manifest.jsonl", "r") as f:
        for line in f:
            try:
                d = json.loads(line)
                if d['event'] == 'ingest':
                    ingested_files.append(d)
            except: continue

    # 2. Множество для отслеживания уже обработанных хэшей в ЭТОМ прогоне
    processed_hashes = set()
    
    duplicates_dir = project_path / "files" / "duplicates"
    duplicates_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for entry in ingested_files:
        f_hash = entry['hash']
        src_path = Path(entry['src'])
        
        # Если файла уже нет (например, перемещен), пропускаем
        if not src_path.exists():
            continue

        # Проверка на дубликат (если хэш уже встречался в processed_hashes)
        if f_hash in processed_hashes:
            dst = duplicates_dir / src_path.name
            if dry_run:
                typer.echo(f"DUPLICATE: {src_path.name} -> duplicates/")
            else:
                if mode == "move":
                    shutil.move(src_path, dst)
                else:
                    shutil.copy2(src_path, dst)
                
                # Пишем в манифест
                append_manifest(project_path, {
                    "ts": datetime.now().isoformat(),
                    "event": "organize",
                    "hash": f_hash,
                    "src": str(src_path),
                    "kind": "duplicate",
                    "status": "duplicate",
                    "dst": str(dst),
                    "duplicate_of": f_hash
                })
                typer.echo(f"DUPLICATE: {src_path.name}")
            continue

        # Если это ПЕРВЫЙ раз, когда мы видим этот хэш — обрабатываем нормально
        cache_file = project_path / "cache" / f"{f_hash}.json"
        if not cache_file.exists():
            # Если кэша нет, значит extract еще не запускали или файл пропущен
            continue
            
        with open(cache_file, 'r') as f:
            data = extract.ExtractedDoc(**json.load(f))
            
        res = organize.organize_file(src_path, data, project_path, f_hash, mode, dry_run)
        
        # Добавляем хэш в список обработанных
        processed_hashes.add(f_hash)
        
        append_manifest(project_path, {
            "ts": datetime.now().isoformat(),
            "event": "organize",
            "hash": f_hash,
            "src": str(src_path),
            "kind": data.doc_type,
            "status": res['status'],
            "dst": res['dst']
        })
        
        typer.echo(f"{res['status'].upper()}: {src_path.name} -> {Path(res['dst']).name}")
        count += 1
    
    if count == 0:
        typer.echo("No extracted files found to organize.")

@app.command()
def fix(
    hash_part: str = typer.Argument(..., help="First few chars of file hash"),
    project_path: Path = typer.Option(..., "--project-path", "-p"),
    date: str = typer.Option(None, help="New date YYYY-MM-DD"),
    amount: float = typer.Option(None, help="New total amount"),
    merchant: str = typer.Option(None, help="New merchant name"),
    currency: str = typer.Option(None, help="New currency")
):
    """Manually fix data in cache for a specific file."""
    cache_dir = project_path / "cache"
    
    # 1. Поиск файла по части хэша
    found_files = list(cache_dir.glob(f"{hash_part}*.json"))
    
    if len(found_files) == 0:
        typer.echo(f"No file found starting with {hash_part}")
        raise typer.Exit(1)
    if len(found_files) > 1:
        typer.echo(f"Ambiguous hash part. Found multiple: {[f.name for f in found_files]}")
        raise typer.Exit(1)
        
    target_file = found_files[0]
    
    # 2. Загрузка JSON
    with open(target_file, 'r') as f:
        data = json.load(f)
    
    typer.echo(f"Fixing {target_file.name}...")
    changes = []

    # 3. Применение правок
    if date:
        data['doc_date'] = date
        # Если мы исправили дату, убираем её из uncertain
        if 'doc_date' in data.get('uncertain_fields', []):
            data['uncertain_fields'].remove('doc_date')
        changes.append(f"date={date}")
        
    if amount is not None:
        data['total_amount'] = amount
        if 'total_amount' in data.get('uncertain_fields', []):
            data['uncertain_fields'].remove('total_amount')
        changes.append(f"amount={amount}")
        
    if merchant:
        data['merchant'] = merchant
        changes.append(f"merchant={merchant}")

    if currency:
        data['currency'] = currency
        changes.append(f"currency={currency}")

    # Повышаем уверенность, так как правил человек
    data['confidence'] = 1.0
    
    # 4. Сохранение
    with open(target_file, 'w') as f:
        json.dump(data, f, indent=2)
        
    typer.echo(f"Updated: {', '.join(changes)}. Confidence set to 1.0.")
    typer.echo("Tip: Run 'organize-cmd' and 'export-cmd' to apply changes.")

@app.command()
def export_cmd(
    project_path: Path = typer.Option(..., "--project-path", "-p"),
    xlsx_name: str = "master.xlsx"
):
    """Generate Master Excel."""
    out_path = project_path / "outputs" / xlsx_name
    export.generate_master_excel(project_path, out_path)

if __name__ == "__main__":
    app()