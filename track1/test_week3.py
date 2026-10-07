"""Offline regression checks for worker failures and repeat-test evidence."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

import repeat_check
import stress_test
import worker


TEST_TMP = Path(__file__).resolve().parent.parent / "tmp" / "week3-tests"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class Week3Tests(unittest.TestCase):
    def test_worker_failure_preserves_detail(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            jobs = Path(directory)
            request = jobs / "abcd1234.request.json"
            request.write_text(json.dumps({"job_id": "abcd1234", "slug": "test", "bbox": {}}))
            detail = "track2/priority.py failed:\nOnly 12 usable grid cells - area too small or too cloudy."
            with patch.object(worker, "JOBS", jobs), patch.object(worker, "venv_python", return_value="python"), patch.object(worker, "run_step", side_effect=RuntimeError(detail)), contextlib.redirect_stdout(io.StringIO()):
                # Box keys are needed before invoking the mocked subprocess.
                request.write_text(json.dumps({"job_id": "abcd1234", "slug": "test", "bbox": dict(south=20, west=85, north=20.1, east=85.1)}))
                worker.process(request)
            status = json.loads((jobs / "abcd1234.status.json").read_text())
            self.assertEqual(status["status"], "failed")
            self.assertIn("Draw a bigger box", status["error"])
            self.assertEqual(status["error_detail"], detail)

    def test_unknown_error_has_plain_fallback(self):
        self.assertNotIn("Traceback", worker.friendly_error("Traceback: unexpected failure"))

    def test_recovery_requeues_only_interrupted_jobs(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            jobs = Path(directory)
            for job_id, state in [("abcd1234", "running"), ("abcd5678", "failed")]:
                (jobs / f"{job_id}.request.json").write_text("{}")
                (jobs / f"{job_id}.status.json").write_text(json.dumps({"status": state}))
            with patch.object(worker, "JOBS", jobs), contextlib.redirect_stdout(io.StringIO()):
                worker.requeue_interrupted()
            self.assertEqual([p.stem for p in worker_requests(jobs)], ["abcd1234.request"])

    def test_repeat_detects_grid_and_mask_changes_and_empty_data(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            data = Path(directory)
            before, after = data / "_repeat" / "test", data / "test"
            before.mkdir(parents=True)
            after.mkdir()
            cases = {
                "rgb": (np.ones((2, 2)), np.ones((2, 2)), "EPSG:4326", "EPSG:3857"),
                "ndvi": (np.ones((2, 2)), np.array([[np.nan, 1], [1, 1]]), "EPSG:4326", "EPSG:4326"),
                "ndbi": (np.full((2, 2), np.nan), np.full((2, 2), np.nan), "EPSG:4326", "EPSG:4326"),
                "ndwi": (np.ones((2, 2)), np.ones((2, 2)), "EPSG:4326", "EPSG:4326"),
                "lst": (np.ones((2, 2)), np.full((2, 2), 2), "EPSG:4326", "EPSG:4326"),
            }
            for name, (a, b, crs_a, crs_b) in cases.items():
                for folder, values, crs in [(before, a, crs_a), (after, b, crs_b)]:
                    with rasterio.open(folder / f"{name}.tif", "w", driver="GTiff", width=2, height=2, count=1, dtype="float32", nodata=np.nan, crs=crs, transform=from_origin(85, 21, 0.01, 0.01)) as dst:
                        dst.write(values.astype("float32"), 1)
            for folder in (before, after):
                (folder / "meta.json").write_text('{"stats": {"lst_mean_c": 1}}')
            with patch.object(repeat_check, "DATA", data), contextlib.redirect_stdout(io.StringIO()):
                repeat_check.compare("test")
            report = (data / "repeat_test.md").read_text()
            self.assertIn("DIFFERENT GRID", report)
            self.assertIn("CHANGED VALID MASK", report)
            self.assertIn("NOT MEASURED", report)
            self.assertIn("identical", report)
            self.assertIn("CHANGED |", report)

    def test_stress_report_keeps_both_rounds(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            data = Path(directory)
            with patch.object(stress_test, "JOBS", data / "jobs"), patch.object(stress_test, "ROOT", data), patch.object(stress_test, "REPORT", data / "stress_test.md"), contextlib.redirect_stdout(io.StringIO()):
                for _ in range(2):
                    job_id = stress_test.queue(*stress_test.BOXES[0])
                    (stress_test.JOBS / f"{job_id}.status.json").write_text(json.dumps({"status": "done", "updated_at": stress_test.now()}))
                stress_test.write_report()
                self.assertEqual((data / "stress_test.md").read_text().count("| coastal |"), 2)


def worker_requests(jobs):
    with patch.object(worker, "JOBS", jobs):
        return worker.waiting_requests()


if __name__ == "__main__":
    unittest.main()
