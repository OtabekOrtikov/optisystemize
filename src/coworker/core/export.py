import pandas as pd
import json
from pathlib import Path
from rich.console import Console # Added for consistent logging if needed
from .storage import Workspace
from .models import ExtractedData
from .i18n import t

console = Console()
import json
from pathlib import Path
from .storage import Workspace
from .models import ExtractedData

def generate_master_excel(workspace: Workspace, output_path: Path, dev_mode: bool = False):
    """Generates the master Excel report with v2.0 sheets and structure."""
    
    if not workspace.manifest_path.exists():
        return

    # Gather data from cache (source of truth for extraction)
    rows = []
    
    for cache_file in workspace.cache.glob("*.json"):
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                extracted = ExtractedData(**data)
                
                # Base User Columns
                # Base User Columns
                row = {
                    t('export.cols.date'): extracted.doc_date,
                    t('export.cols.category'): extracted.doc_type, 
                    t('export.cols.merchant'): extracted.merchant,
                    t('export.cols.amount'): extracted.total_amount,
                    t('export.cols.currency'): extracted.currency,
                    t('export.cols.summary'): extracted.summary,
                    t('export.cols.notes'): extracted.review_reason if extracted.is_review_needed else ""
                }
                
                # Add Dev columns
                # Add Dev columns
                if dev_mode:
                    row.update({
                        t('export.cols.hash'): cache_file.stem,
                        t('export.cols.confidence'): extracted.confidence,
                        t('export.cols.time'): extracted.processing_time,
                        t('export.cols.tokens'): extracted.token_usage.get("total_tokens", 0)
                    })
                
                # In user mode, we skip these
                    
                rows.append(row)
        except:
            continue
            
    if not rows:
        return

    df = pd.DataFrame(rows)
    
    # Reorder columns for user friendliness
    # Reorder columns for user friendliness
    user_cols = [
        t('export.cols.date'), 
        t('export.cols.category'), 
        t('export.cols.merchant'), 
        t('export.cols.amount'), 
        t('export.cols.currency'), 
        t('export.cols.summary'), 
        t('export.cols.notes')
    ]
    if dev_mode:
        cols = user_cols + [
            t('export.cols.hash'), 
            t('export.cols.confidence'), 
            t('export.cols.time'), 
            t('export.cols.tokens')
        ]
    else:
        # Remove technical columns from user view
        cols = user_cols
        
    # Filter/Order available columns
    final_cols = [c for c in cols if c in df.columns]
    df = df[final_cols]
    
    # Create Excel with multiple sheets
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # Sheet 1: All Documents
        df.to_excel(writer, sheet_name=t('export.sheets.all_docs'), index=False)
        
        # Sheet 2: Monthly Breakdown (requires Date)
        # Convert Date to datetime for grouping
        col_date = t('export.cols.date')
        col_cat = t('export.cols.category')
        col_amt = t('export.cols.amount')
        
        df_dates = df.copy()
        df_dates[col_date] = pd.to_datetime(df_dates[col_date], errors='coerce')
        if not df_dates[col_date].isna().all():
            df_dates['Month'] = df_dates[col_date].dt.to_period('M')
            # Pivot table: Rows=Month, Cols=Category, Vals=Amount
            monthly = df_dates.groupby(['Month', col_cat])[col_amt].sum().unstack(fill_value=0)
            monthly.to_excel(writer, sheet_name=t('export.sheets.monthly'))

        # Sheet 3: Review Needed
        col_notes = t('export.cols.notes')
        if col_notes in df.columns:
            review_df = df[df[col_notes] != ""]
            if not review_df.empty:
                review_sheet_cols = [t('export.cols.date'), t('export.cols.merchant'), t('export.cols.amount'), col_notes]
                if dev_mode: review_sheet_cols.append(t('export.cols.hash'))
                # Ensure cols exist
                avail_review = [c for c in review_sheet_cols if c in df.columns]
                review_df[avail_review].to_excel(writer, sheet_name=t('export.sheets.review'), index=False)
            
        # Sheet 4: Performance (Dev Only)
        if dev_mode:
            perf_df = df[[t('export.cols.hash'), t('export.cols.time'), t('export.cols.tokens'), t('export.cols.confidence')]]
            perf_df.to_excel(writer, sheet_name=t('export.sheets.system'), index=False)
        
    console.print(t('cli.run.paths.spreadsheet', path=output_path))

def generate_review_csv(workspace: Workspace):
    """Generates a CSV for files needing review."""
    output_path = workspace.review / "review.csv"
    
    rows = []
    for cache_file in workspace.cache.glob("*.json"):
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                extracted = ExtractedData(**data)
                
                if extracted.is_review_needed:
                    rows.append({
                        t('export.cols.file_name'): cache_file.stem, 
                        t('export.cols.reason'): extracted.review_reason or "Unknown",
                        t('export.cols.action'): "Check and Rename"
                    })
        except:
            continue
            
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        # console.print handled in cli or we can print here

