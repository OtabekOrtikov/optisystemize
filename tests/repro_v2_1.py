import shutil
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from coworker.core import organize, export, models, storage

class TestV2_1(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_workspace")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        
        self.ws = storage.Workspace(self.test_dir)
        self.ws.ensure_structure()
        self.ws.ensure_system_only() # Ensure hidden dirs
        
        # Create a dummy file
        self.src_file = self.test_dir / "test_doc.pdf"
        self.src_file.touch()
        
    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_safe_move_creates_backup(self):
        """Test that mode='move' creates a backup in trash_dir."""
        data = models.ExtractedData(
            doc_type="Receipt",
            doc_date="2024-01-01",
            merchant="TestStore",
            total_amount=100.0,
            currency="USD",
            summary="Test receipt"
        )
        
        run_id = "run_123"
        trash_dir = self.ws.system / "trash" / run_id
        
        # Execute organize
        res = organize.organize_file(
            src_path=self.src_file,
            data=data,
            workspace=self.ws,
            f_hash="abc123hash",
            dry_run=False,
            mode="move",
            trash_dir=trash_dir
        )
        
        # Check result
        self.assertEqual(res['status'], models.FileStatus.ORGANIZED)
        
        # Original should be gone (moved)
        self.assertFalse(self.src_file.exists())
        
        # Destination should exist
        dest_path = Path(res['dst'])
        self.assertTrue(dest_path.exists())
        
        # Backup should exist
        # logic: trash_dir / rel_path -> test_doc.pdf is in root of workspace?
        # src_file is test_workspace/test_doc.pdf. ws.root is test_workspace.
        # rel_path is test_doc.pdf.
        backup_path = trash_dir / "test_doc.pdf"
        self.assertTrue(backup_path.exists())

    def test_review_csv_generation(self):
        """Test that review.csv is generated correctly."""
        # Create a mock cache file
        cache_file = self.ws.cache / "hash123.json"
        data = models.ExtractedData(
            doc_type="Unknown",
            is_review_needed=True,
            review_reason="Low confidence",
            confidence=0.5
        )
        with open(cache_file, "w") as f:
            f.write(data.model_dump_json())
            
        export.generate_review_csv(self.ws)
        
        csv_path = self.ws.review / "review.csv"
        self.assertTrue(csv_path.exists())
        
        with open(csv_path, "r") as f:
            content = f.read()
            self.assertIn("hash123", content)
            self.assertIn("Low confidence", content)

    def test_master_excel_cleanup(self):
        """Test that master.xlsx excludes technical columns by default."""
        cache_file = self.ws.cache / "hash456.json"
        data = models.ExtractedData(
            doc_type="Receipt",
            merchant="Vendor",
            total_amount=50.0,
            confidence=0.9,
            token_usage={"total_tokens": 100}
        )
        with open(cache_file, "w") as f:
            f.write(data.model_dump_json())
            
        # Run export (default dev_mode=False)
        export_path = self.ws.root / "master.xlsx"
        export.generate_master_excel(self.ws, export_path, dev_mode=False)
        
        import pandas as pd
        df = pd.read_excel(export_path, sheet_name="All Documents")
        
        self.assertIn("Merchant", df.columns)
        self.assertNotIn("Tokens", df.columns)
        self.assertNotIn("Hash", df.columns)
        
        # Check Sheets
        xl = pd.ExcelFile(export_path)
        self.assertNotIn("System Stats", xl.sheet_names)
        
        # Run export with dev_mode=True
        export.generate_master_excel(self.ws, export_path, dev_mode=True)
        df_dev = pd.read_excel(export_path, sheet_name="All Documents")
        self.assertIn("Tokens", df_dev.columns)
        
        xl_dev = pd.ExcelFile(export_path)
        self.assertIn("System Stats", xl_dev.sheet_names)

if __name__ == "__main__":
    unittest.main()
