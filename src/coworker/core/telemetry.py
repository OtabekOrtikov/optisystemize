import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from .storage import Workspace

class RunMetrics(BaseModel):
    run_id: str
    start_time: float
    end_time: float = 0.0
    total_files: int = 0
    processed_files: int = 0
    cached_skips: int = 0 # Files served from cache
    requests_total: int = 0 # Actual Gemini API calls
    errors: int = 0
    review_needed: int = 0
    
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_ai_time: float = 0.0
    
    stage_times: Dict[str, float] = Field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

class Telemetry:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metrics = RunMetrics(
            run_id=self.run_id,
            start_time=time.time()
        )
        
        # Ensure runs dir exists
        self.runs_dir = self.workspace.system / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def start_stage(self, stage_name: str):
        self.metrics.stage_times[f"{stage_name}_start"] = time.time()

    def end_stage(self, stage_name: str):
        start = self.metrics.stage_times.get(f"{stage_name}_start")
        if start:
            duration = time.time() - start
            self.metrics.stage_times[stage_name] = duration

    def log_file_processed(self, extracted_data: Any = None, error: bool = False):
        self.metrics.total_files += 1
        if error:
            self.metrics.errors += 1
            return

        self.metrics.processed_files += 1
        if extracted_data:
            if extracted_data.is_review_needed:
                self.metrics.review_needed += 1
            
            # Check for cache flag - assumes model has _is_cached
            is_cached = getattr(extracted_data, "_is_cached", False)
            
            if is_cached:
                self.metrics.cached_skips += 1
                # Do NOT add tokens or AI time for cached files
            else:
                self.metrics.processed_files += 1 # Only count freshly processed here? Or Total Processed = Cached + Fresh?
                # User said: "Files Processed 9/9... but taken from cache".
                # Let's keep processed_files as total SUCCESSFUL extractions (cached or fresh).
                # But separate Requests.
                self.metrics.requests_total += 1
                self.metrics.total_ai_time += extracted_data.processing_time
                if extracted_data.token_usage:
                    self.metrics.total_tokens_input += extracted_data.token_usage.get("prompt_tokens", 0)
                    self.metrics.total_tokens_output += extracted_data.token_usage.get("candidates_tokens", 0)
        else:
             # Non-extracted result? Or just file move? 
             # For ingest, we call log_file_processed? No, ingest is part of Total Files.
             # This method is called after organize/extract.
             # Let's assume if extracted_data is None it's just a count.
             self.metrics.processed_files += 1 # Fallback behavior
             pass

    def save(self):
        self.metrics.end_time = time.time()
        
        # Save individual run
        run_file = self.runs_dir / f"{self.run_id}.json"
        
        # Correct mkdir reuse check
        if not self.runs_dir.exists():
            self.runs_dir.mkdir(parents=True, exist_ok=True)
            
        with open(run_file, "w") as f:
            f.write(self.metrics.model_dump_json(indent=2))
            
        # Update aggregate metrics (simple append or recalc?)
        # For now, we rely on individual run files.
