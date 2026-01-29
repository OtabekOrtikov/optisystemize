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
    
    # Check if inbox_path is the same as root (Ad-hoc mode usually)
    # If so, we must be careful not to recurse into Organized/ etc.
    # iterdir() is shallow, so we just need to skip if the item IS one of those dirs
    # But wait, iterdir() returns files too.
    # If the user has subfolders in their 'Receipts' folder, we might want to walk them?
    # The current implementation uses os.walk in v1, but here it uses iterdir() (shallow).
    # If we want shallow scan (safest for ad-hoc):
    
    for item in inbox_path.iterdir():
        # Skip hidden/excluded
        if item.name.startswith('.') or item.name in exclude_dirs:
            continue
            
        if item.is_file() and item.suffix.lower() in extensions:
            yield item
        # If we want recursive later, we'd add logic here. For now shallow is safer for Ad-hoc.
