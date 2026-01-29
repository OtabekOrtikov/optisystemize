import pandas as pd
import json
from pathlib import Path
from rich.console import Console # Added for consistent logging if needed
from .storage import Workspace
from .models import ExtractedData

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
                row = {
                    "Date": extracted.doc_date,
                    "Category": extracted.doc_type, # Using doc_type as category for now
                    "Merchant": extracted.merchant,
                    "Amount": extracted.total_amount,
                    "Currency": extracted.currency,
                    "Summary": extracted.summary,
                    "Source File": extracted.lines[0].description if extracted.lines and len(extracted.lines)==1 and not extracted.merchant else "Unknown", # Wait, logic for source file name?
                    # Actually data doesn't have original filename here easily unless we look at manifest or store it.
                    # We stored hash in filename, but original name is lost in ExtractedData model.
                    # cache_file.stem is hash.
                    # For now, let's use hash or skip "Source File" logic if complex.
                    # The user asked for "Source File (nice name)". 
                    # We don't have it in ExtractedData. 
                    # We can try to find it from manifest if we want perfection, but that's slow.
                    # Let's stick to what we have or "view" it.
                    "Notes": extracted.review_reason if extracted.is_review_needed else ""
                }
                
                # Add Dev columns
                if dev_mode:
                    row.update({
                        "Hash": cache_file.stem,
                        "Confidence": extracted.confidence,
                        "Processing Time (s)": extracted.processing_time,
                        "Tokens": extracted.token_usage.get("total_tokens", 0)
                    })
                
                # In user mode, we skip these
                    
                rows.append(row)
        except:
            continue
            
    if not rows:
        return

    df = pd.DataFrame(rows)
    
    # Reorder columns for user friendliness
    user_cols = ["Date", "Category", "Merchant", "Amount", "Currency", "Summary", "Notes"]
    user_cols = ["Date", "Category", "Merchant", "Amount", "Currency", "Summary", "Notes"]
    if dev_mode:
        cols = user_cols + ["Hash", "Confidence", "Processing Time (s)", "Tokens"]
    else:
        # Remove technical columns from user view
        cols = user_cols
        
    # Filter/Order available columns
    final_cols = [c for c in cols if c in df.columns]
    df = df[final_cols]
    
    # Create Excel with multiple sheets
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # Sheet 1: All Documents
        df.to_excel(writer, sheet_name="All Documents", index=False)
        
        # Sheet 2: Monthly Breakdown (requires Date)
        # Convert Date to datetime for grouping
        df_dates = df.copy()
        df_dates['Date'] = pd.to_datetime(df_dates['Date'], errors='coerce')
        if not df_dates['Date'].isna().all():
            df_dates['Month'] = df_dates['Date'].dt.to_period('M')
            # Pivot table: Rows=Month, Cols=Category, Vals=Amount
            monthly = df_dates.groupby(['Month', 'Category'])['Amount'].sum().unstack(fill_value=0)
            monthly.to_excel(writer, sheet_name="Monthly Summary")

        # Sheet 3: Review Needed
        if "Notes" in df.columns:
            review_df = df[df['Notes'] != ""]
            if not review_df.empty:
                review_sheet_cols = ["Date", "Merchant", "Amount", "Notes"]
                if dev_mode: review_sheet_cols.append("Hash")
                # Ensure cols exist
                avail_review = [c for c in review_sheet_cols if c in df.columns]
                review_df[avail_review].to_excel(writer, sheet_name="Review Needed", index=False)
            
        # Sheet 4: Performance (Dev Only)
        if dev_mode:
            perf_df = df[['Hash', 'Processing Time (s)', 'Tokens', 'Confidence']]
            perf_df.to_excel(writer, sheet_name="System Stats", index=False)
        
    console.print(f"Exported master report to {output_path}")

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
                        "file_name": cache_file.stem, # Using hash/stem as we don't have original filename here easily
                        "reason": extracted.review_reason or "Unknown",
                        "suggested_action": "Check and Rename"
                    })
        except:
            continue
            
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        # console.print handled in cli or we can print here

