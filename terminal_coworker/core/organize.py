import shutil
from pathlib import Path
from datetime import datetime
import re
from terminal_coworker.models import ExtractedDoc

def needs_review(doc: ExtractedDoc) -> bool:
    if doc.confidence < 0.70:
        return True
    if not doc.doc_date or 'doc_date' in doc.uncertain_fields:
        return True
    if not doc.total_amount or 'total_amount' in doc.uncertain_fields:
        return True
    return False

def clean_filename(s: str) -> str:
    if not s: return "unknown"
    # Remove invalid chars, replace spaces with _, keep simple
    s = str(s).strip()
    return re.sub(r'[^a-zA-Z0-9\-_]', '', s.replace(' ', '_'))

def get_target_path(
    project_path: Path, 
    doc: ExtractedDoc, 
    original_ext: str, 
    file_hash: str
) -> Path:
    
    # 1. Base Folder
    if doc.doc_date:
        try:
            date_obj = datetime.strptime(doc.doc_date, "%Y-%m-%d")
            year_folder = str(date_obj.year)
            month_folder = f"{date_obj.year}-{date_obj.month:02d}"
            base = project_path / "files" / year_folder / month_folder / doc.doc_type
        except ValueError:
             base = project_path / "files" / "unknown_date" / doc.doc_type
    else:
        base = project_path / "files" / "unknown_date" / doc.doc_type

    # 2. Filename Construction
    # Template: Date__Type__Merchant__AmountCurrency__ShortHash.ext
    date_part = doc.doc_date if doc.doc_date else "unknown_date"
    merchant_part = clean_filename(doc.merchant)
    
    amount_part = "unknown"
    if doc.total_amount is not None:
        curr = clean_filename(doc.currency) if doc.currency else ""
        amount_part = f"{doc.total_amount}{curr}"
        
    short_hash = file_hash[:8]
    new_name = f"{date_part}__{doc.doc_type}__{merchant_part}__{amount_part}__{short_hash}{original_ext}"
    
    return base / new_name

def organize_file(
    src_path: Path, 
    extracted: ExtractedDoc, 
    project_path: Path, 
    file_hash: str, 
    mode: str = "copy", 
    dry_run: bool = False
) -> dict:
    
    target_path = get_target_path(project_path, extracted, src_path.suffix, file_hash)
    is_review = needs_review(extracted)
    
    actions = []
    
    if dry_run:
        actions.append(f"Would {mode} {src_path.name} -> {target_path}")
        if is_review:
            actions.append(f"Would copy to needs_review")
        return {"status": "dry_run", "dst": str(target_path), "notes": "; ".join(actions)}

    # Ensure dirs exist
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Main Operation
    if mode == "move":
        shutil.move(src_path, target_path)
    else:
        shutil.copy2(src_path, target_path)
        
    # Handle Needs Review (Copy to review folder)
    if is_review:
        review_dir = project_path / "files" / "needs_review"
        review_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_path, review_dir / target_path.name)
        
    status = "needs_review" if is_review else "sorted"
    return {"status": status, "dst": str(target_path)}