from pathlib import Path
from typing import Optional
import typer

class Workspace:
    def __init__(self, root: Path):
        self.root = root.absolute()
        
        # User facing folders
        self.inbox = self.root / "Inbox"
        self.organized = self.root / "Organized"
        self.exports = self.root / "Exports"
        self.review = self.root / "Review"
        
        # System folders
        self.system = self.root / ".coworker"
        self.cache = self.system / "cache"
        self.logs = self.system / "logs"
        self.manifest_path = self.system / "manifest.jsonl"
        self.config_path = self.system / "config.yml"

    def ensure_structure(self):
        """Create necessary directories."""
        for p in [self.inbox, self.organized, self.exports, self.review, 
                  self.system, self.cache, self.logs]:
            p.mkdir(parents=True, exist_ok=True)
        
        if not self.manifest_path.exists():
            self.manifest_path.touch()

    def ensure_system_only(self):
        """Create only system directories for ad-hoc runs."""
        for p in [self.system, self.cache, self.logs]:
            p.mkdir(parents=True, exist_ok=True)
            
        if not self.manifest_path.exists():
            self.manifest_path.touch()

    def is_valid(self) -> bool:
        """Check if this is a valid workspace."""
        return self.system.exists() and self.manifest_path.exists()

def get_workspace(path: Optional[Path] = None) -> Workspace:
    """Get workspace from path or current directory."""
    if path is None:
        path = Path.cwd()
    
    ws = Workspace(path)
    if not ws.is_valid():
        # Maybe the user calls it from inside a workspace?
        # Try parent? For now, keep it strict. 
        # If folder structure doesn't exist, we might be in 'init' phase or incorrect usage.
        pass 
    return ws
