import pandas as pd
from pathlib import Path
import json
import re

def clean_sheet_name(name: str) -> str:
    """Removes characters forbidden in Excel sheet names: \ / ? * [ ]"""
    if not name:
        return "Unknown"
    # Заменяем запрещенные символы на '_'
    safe_name = re.sub(r'[\\/*?:\[\]]', '_', str(name))
    # Обрезаем до 31 символа (лимит Excel)
    return safe_name[:31]

def generate_master_excel(project_path: Path, output_path: Path):
    cache_dir = project_path / "cache"
    manifest_path = project_path / "manifest.jsonl"
    
    records = []
    
    # 1. Load Manifest for file tracking
    manifest_map = {}
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    # Keep latest status for each hash
                    manifest_map[entry['hash']] = entry
                except json.JSONDecodeError:
                    continue

    # 2. Iterate Cache to build data
    if not cache_dir.exists():
        print("Cache directory not found. Nothing to export.")
        return

    for json_file in cache_dir.glob("*.json"):
        file_hash = json_file.stem
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Skipping broken cache file: {json_file}")
            continue
            
        row = data.copy()
        row['hash'] = file_hash
        # Convert list to string for Excel
        uncert = row.get('uncertain_fields', [])
        row['uncertain_fields'] = ", ".join(uncert) if isinstance(uncert, list) else str(uncert)
        
        # Merge with manifest info
        m_entry = manifest_map.get(file_hash, {})
        row['source_file'] = m_entry.get('src')
        row['status'] = m_entry.get('status')
        row['final_path'] = m_entry.get('dst')
        
        # Add Month column for grouping
        if row.get('doc_date') and len(row['doc_date']) >= 7:
            row['month'] = row['doc_date'][:7] # YYYY-MM
        else:
            row['month'] = 'Unknown'
            
        records.append(row)

    if not records:
        print("No data to export.")
        return

    df = pd.DataFrame(records)
    
    # Ensure output dir exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 3. Create Excel Writer
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet: All
            df.to_excel(writer, sheet_name="All", index=False)
            
            # Sheet: Review (Filter)
            # Safe filtering handling N/A values
            mask_confidence = df['confidence'] < 0.7
            mask_date = df['doc_date'].isnull() | df['doc_date'].str.contains(r'\?', na=False)
            mask_amount = df['total_amount'].isnull()
            
            review_df = df[mask_confidence | mask_date | mask_amount]
            review_df.to_excel(writer, sheet_name="Review", index=False)
            
            # Sheet: Monthly
            months = df['month'].unique()
            for m in months:
                if not m: continue
                month_df = df[df['month'] == m]
                
                # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
                sheet_title = clean_sheet_name(m) 
                
                month_df.to_excel(writer, sheet_name=sheet_title, index=False)
                
        print(f"Master Excel created at: {output_path}")
        
    except Exception as e:
        print(f"Failed to write Excel: {e}")