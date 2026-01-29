import shutil
import re
from pathlib import Path
from typing import Dict, Any, List, Counter

from .models import ExtractedData, FileStatus, OrganizationMode, CategoriesMode
from .storage import Workspace
from .config import settings

def sanitize_filename(name: str) -> str:
    
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip().replace(' ', '_')
    return name[:50]  

def get_target_category(doc_type: str, all_categories: Counter, max_categories: int) -> str:
    
    
    return doc_type

def organize_file(
    src_path: Path, 
    data: ExtractedData, 
    workspace: Workspace,
     f_hash: str,
    dry_run: bool = False,
    mode: str = "copy",
    trash_dir: Path = None
) -> Dict[str, Any]:
    
    
    category = data.doc_type
    
    
    
    
    
    
    if data.is_review_needed:
        
        dest_folder = workspace.review
        reason = data.review_reason or "Review"
        
        reason_folder = sanitize_filename(reason)
        target_dir = dest_folder / reason_folder
    else:
        
        date_folder = "Unknown_Date"
        if data.doc_date:
            try:
                date_folder = data.doc_date[:7] 
            except: pass
        
        target_dir = workspace.organized / date_folder / category

    
    
    ext = src_path.suffix
    
    parts = []
    parts.append(data.doc_date if data.doc_date else "Unknown")
    parts.append(category)
    parts.append(sanitize_filename(data.merchant) if data.merchant else "Unknown")
    
    amt = f"{data.total_amount}" if data.total_amount else "0"
    curr = data.currency if data.currency else ""
    parts.append(f"{amt}{curr}")
    
    
    short_hash = f_hash[:8]
    parts.append(short_hash)
    
    base_name = "__".join(parts)
    new_name = f"{base_name}{ext}"

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        
        
        dest_path = target_dir / new_name
        counter = 1
        while dest_path.exists():
             dest_path = target_dir / f"{base_name}_{counter}{ext}"
             counter += 1
             
        if mode == "move":
            
            if trash_dir:
                
                
                
                
                
                try:
                    rel_path = src_path.relative_to(workspace.root)
                    backup_path = trash_dir / rel_path
                except ValueError:
                    
                    backup_path = trash_dir / src_path.name
                
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, backup_path)
            
            shutil.move(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)
        return {
            "status": FileStatus.ORGANIZED,
            "dst": str(dest_path)
        }
    else:
        return {
            "status": FileStatus.SKIPPED,
            "dst": "dry-run"
        }
