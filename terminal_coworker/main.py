import typer
from pathlib import Path
from datetime import datetime
import json
import os
import shutil
from typing import Optional

from terminal_coworker.utils import calculate_sha256
from terminal_coworker.core import extract, organize as org_module, export
from terminal_coworker.models import ManifestEntry

app = typer.Typer()

def append_manifest(project_path: Path, entry: dict):
    with open(project_path / "manifest.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

@app.command()
def init(project_path: Path = typer.Argument(".", help="Where to create the project")):
    """Create project structure."""
    dirs = ["inbox", "files", "cache", "outputs"]
    for d in dirs:
        (project_path / d).mkdir(parents=True, exist_ok=True)
    
    manifest = project_path / "manifest.jsonl"
    if not manifest.exists():
        manifest.touch()
    typer.echo(f"✅ Initialized at {project_path.absolute()}")

@app.command()
def organize(
    project_path: Path = typer.Argument(".", help="Project folder (default: current dir)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-extraction"),
    mode: str = typer.Option("copy", help="copy or move source files")
):
    """🚀 RUN PIPELINE: Auto-collect files -> Extract -> Sort -> Export"""
    
    typer.echo("🚀 OptiSystemize: Working...")
    
    # --- 0. АВТОМАТИЧЕСКАЯ ПОДГОТОВКА (Магия) ---
    # Создаем структуру, если её нет
    dirs = ["inbox", "files", "cache", "outputs"]
    for d in dirs:
        (project_path / d).mkdir(parents=True, exist_ok=True)
    
    # Собираем "бесхозные" картинки в текущей папке и кидаем в inbox
    inbox_path = project_path / "inbox"
    supported_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
    moved_count = 0
    
    # Проходим по файлам в корне проекта
    for item in project_path.iterdir():
        if item.is_file() and item.suffix.lower() in supported_extensions:
            # Не трогаем файлы, если они уже внутри системных папок (хотя iterdir не рекурсивен, так что ок)
            try:
                shutil.move(str(item), str(inbox_path / item.name))
                moved_count += 1
            except shutil.Error:
                pass # Если файл уже есть в inbox, пропускаем

    if moved_count > 0:
        typer.echo(f"🧹 Auto-moved {moved_count} files to 'inbox/' folder.")

    # --- 1. INGEST (Регистрация) ---
    ingest_count = 0
    for root, _, files in os.walk(inbox_path):
        for name in files:
            file_path = Path(root) / name
            if name.startswith('.'): continue
            
            f_hash = calculate_sha256(file_path)
            entry = ManifestEntry(
                ts=datetime.now().isoformat(),
                event="ingest",
                hash=f_hash,
                src=str(file_path.absolute()),
                kind="file",
                status="new"
            )
            append_manifest(project_path, entry.model_dump())
            ingest_count += 1
    
    if ingest_count == 0:
        typer.echo("⚠️ No files found to process.")
        return

    # --- 2. EXTRACT (AI) ---
    typer.echo(f"🧠 Processing {ingest_count} files with AI...")
    files_to_process = {}
    
    # Читаем манифест
    with open(project_path / "manifest.jsonl", "r") as f:
        for line in f:
            try:
                d = json.loads(line)
                if d['event'] == 'ingest':
                    files_to_process[d['hash']] = Path(d['src'])
            except: continue

    for f_hash, src_path in files_to_process.items():
        if not src_path.exists(): continue
        
        cache_path = project_path / "cache" / f"{f_hash}.json"
        if cache_path.exists() and not force:
            continue

        typer.echo(f"   > {src_path.name}")
        result = extract.extract_data(src_path, f_hash, project_path, force)
        status = "extracted" if result else "error"
        
        append_manifest(project_path, {
            "ts": datetime.now().isoformat(),
            "event": "extract",
            "hash": f_hash,
            "src": str(src_path),
            "kind": "image",
            "status": status
        })

    # --- 3. SORT (Сортировка) ---
    typer.echo("🗂 Sorting...")
    processed_hashes = set()
    duplicates_dir = project_path / "files" / "duplicates"
    duplicates_dir.mkdir(parents=True, exist_ok=True)
    
    # Собираем все события ingest заново
    all_ingests = []
    with open(project_path / "manifest.jsonl", "r") as f:
        for line in f:
            try:
                d = json.loads(line)
                if d['event'] == 'ingest': all_ingests.append(d)
            except: continue
            
    for entry in all_ingests:
        f_hash = entry['hash']
        src_path = Path(entry['src'])
        if not src_path.exists(): continue

        # Дубликаты
        if f_hash in processed_hashes:
            dst = duplicates_dir / src_path.name
            if mode == "move": shutil.move(src_path, dst)
            else: shutil.copy2(src_path, dst)
            # typer.echo(f"   Duplicate: {src_path.name}") # Меньше шума в консоли
            continue
            
        # Сортировка
        cache_file = project_path / "cache" / f"{f_hash}.json"
        if not cache_file.exists(): continue
        
        with open(cache_file, 'r') as f:
            data = extract.ExtractedDoc(**json.load(f))
        
        res = org_module.organize_file(src_path, data, project_path, f_hash, mode, dry_run=False)
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

    # --- 4. EXPORT (Excel) ---
    out_path = project_path / "outputs" / "master.xlsx"
    export.generate_master_excel(project_path, out_path)
    
    typer.echo(f"✨ DONE! Report: {out_path}")

@app.command()
def fix(
    hash_part: str = typer.Argument(..., help="First chars of hash"),
    project_path: Path = typer.Option(Path("."), "--project-path", "-p"),
    date: str = typer.Option(None),
    amount: float = typer.Option(None),
    merchant: str = typer.Option(None),
    currency: str = typer.Option(None)
):
    """Manually fix data."""
    cache_dir = project_path / "cache"
    found_files = list(cache_dir.glob(f"{hash_part}*.json"))
    
    if len(found_files) != 1:
        typer.echo("File not found or ambiguous hash.")
        raise typer.Exit(1)
        
    target_file = found_files[0]
    with open(target_file, 'r') as f: data = json.load(f)
    
    if date: 
        data['doc_date'] = date
        if 'doc_date' in data.get('uncertain_fields', []): data['uncertain_fields'].remove('doc_date')
    if amount: 
        data['total_amount'] = amount
        if 'total_amount' in data.get('uncertain_fields', []): data['uncertain_fields'].remove('total_amount')
    if merchant: data['merchant'] = merchant
    if currency: data['currency'] = currency
    data['confidence'] = 1.0
    
    with open(target_file, 'w') as f: json.dump(data, f, indent=2)
    typer.echo(f"Fixed {target_file.name}")

if __name__ == "__main__":
    app()