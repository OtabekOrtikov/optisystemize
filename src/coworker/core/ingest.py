import hashlib
from pathlib import Path
from typing import Iterator
from .config import settings

CHUNK_SIZE = 8192

def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file efficiently."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    return sha256.hexdigest()

def scan_inbox(
    inbox_path: Path, 
    extensions: set = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'},
    exclude_dirs: set = {'Organized', 'Review', 'Exports', '.coworker', 'files'}
) -> Iterator[Path]:
    """Yields supported files from Inbox, skipping system/output folders."""
    if not inbox_path.exists():
        return
    
    
    
    
    
    
    
    
    
    for item in inbox_path.iterdir():
        
        if item.name.startswith('.') or item.name in exclude_dirs:
            continue
            
        if item.is_file() and item.suffix.lower() in extensions:
            yield item
        
