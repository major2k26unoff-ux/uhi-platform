"""Automated tests for the API.   pip install pytest   then   pytest -v

Each test gets its own empty temporary folder, with one tiny fake area in it,
so the tests never touch the real data/ folder.
"""
import json
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    area = data / "testville"
    (area / "preview").mkdir(parents=True)
    (area / "meta.json").write_text(json.dumps({
        "city": "testville", "display_name": "Testville", "bounds": [20.0, 85.0, 20.1, 85.1],
        "stats": {"lst_mean_c": 35.0, "lst_min_c": 28.0, "lst_max_c": 44.0, "ndvi_mean": 0.3}}))
    (area / "preview" / "lst.png").write_bytes(b"\x89PNG fake")
    (area / "priority.geojson").write_text('{"type": "FeatureCollection", "features": []}')
    (area / "priority_summary.json").write_text('{"delta_t": {"top_mean_c": 1.5}}')
    presets = tmp_path / "presets.json"
    presets.write_text(json.dumps([
        {"slug": "testville", "name": "Testville", "bounds": [20.0, 85.0, 20.1, 85.1], "group": "metro"},
        {"slug": "nowhere", "name": "Nowhere", "bounds": [21.0, 86.0, 21.1, 86.1], "group": "hot_town"}]))
    monkeypatch.setattr(main, "DATA_ROOT", data)
    monkeypatch.setattr(main, "JOBS", data / "jobs")
    monkeypatch.setattr(main, "PRESETS", presets)
    return TestClient(main.app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_cities_know_what_is_ready(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["testville"]["ready"] and cities["testville"]["has_priority"]
    assert not cities["nowhere"]["ready"]


def test_results_list_only_existing_layers(client):
    body = client.get("/api/results/testville").json()
    assert body["layer_urls"] == {"lst": "/api/layer/testville/lst.png"}
    assert body["has_priority"] is True


def test_unprocessed_area_is_404(client):
    assert client.get("/api/results/nowhere").status_code == 404


def test_bad_slug_is_rejected(client):
    assert client.get("/api/results/Test_Ville").status_code == 400


def test_priority_endpoints(client):
    assert client.get("/api/priority/testville").json()["type"] == "FeatureCollection"
    assert client.get("/api/priority/testville/summary").json()["delta_t"]["top_mean_c"] == 1.5


def test_analyze_writes_a_request_file(client):
    r = client.post("/api/analyze", json={"south": 20.2, "west": 85.7, "north": 20.3, "east": 85.8})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    request = json.loads((main.JOBS / f"{job_id}.request.json").read_text())
    assert request["slug"] == f"custom-{job_id}"
    assert request["bbox"]["south"] == 20.2


def test_new_job_reports_queued(client):
    job_id = client.post("/api/analyze", json={"south": 20.2, "west": 85.7, "north": 20.3, "east": 85.8}).json()["job_id"]
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "queued"


def test_job_reports_worker_status(client):
    job_id = client.post("/api/analyze", json={"south": 20.2, "west": 85.7, "north": 20.3, "east": 85.8}).json()["job_id"]
    (main.JOBS / f"{job_id}.status.json").write_text(json.dumps({"job_id": job_id, "status": "running", "progress": 40}))
    assert client.get(f"/api/jobs/{job_id}").json()["progress"] == 40


@pytest.mark.parametrize("box", [
    {"south": 20.3, "west": 85.7, "north": 20.2, "east": 85.8},   # upside down
    {"south": 20.0, "west": 85.0, "north": 21.0, "east": 86.0},   # too big
    {"south": 40.0, "west": 10.0, "north": 40.1, "east": 10.1},   # not India
])
def test_bad_boxes_are_refused(client, box):
    assert client.post("/api/analyze", json=box).status_code == 422


def test_unknown_and_invalid_jobs(client):
    assert client.get("/api/jobs/0000ffff").status_code == 404
    assert client.get("/api/jobs/not-a-job").status_code == 400