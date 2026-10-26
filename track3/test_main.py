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
    # ---------- Week 3: zones as a CSV file ----------

# ---------- Week 3: same-box reuse ----------

BOX = {"south": 20.2, "west": 85.7, "north": 20.3, "east": 85.8}


def finish_job(job_id, status="done"):
    """Pretend the worker finished a job: write its status file and, if done, its area folder."""
    request = json.loads((main.JOBS / f"{job_id}.request.json").read_text())
    (main.JOBS / f"{job_id}.status.json").write_text(json.dumps({"job_id": job_id, "status": status}))
    if status == "done":
        (main.DATA_ROOT / request["slug"]).mkdir(parents=True, exist_ok=True)
        (main.DATA_ROOT / request["slug"] / "meta.json").write_text("{}")


def test_same_box_while_queued_reuses_the_job(client):
    first = client.post("/api/analyze", json=BOX).json()
    second = client.post("/api/analyze", json=BOX).json()
    assert second["job_id"] == first["job_id"] and second["reused"] is True
    assert len(list(main.JOBS.glob("*.request.json"))) == 1


def test_same_box_after_done_returns_the_old_result(client):
    first = client.post("/api/analyze", json=BOX).json()
    finish_job(first["job_id"])
    second = client.post("/api/analyze", json=BOX).json()
    assert second["job_id"] == first["job_id"] and second["status"] == "done"


def test_failed_box_can_be_tried_again(client):
    first = client.post("/api/analyze", json=BOX).json()
    finish_job(first["job_id"], status="failed")
    second = client.post("/api/analyze", json=BOX).json()
    assert second["job_id"] != first["job_id"] and second["reused"] is False


def test_done_but_files_deleted_runs_again(client):
    first = client.post("/api/analyze", json=BOX).json()
    finish_job(first["job_id"])
    (main.DATA_ROOT / first["slug"] / "meta.json").unlink()
    assert client.post("/api/analyze", json=BOX).json()["job_id"] != first["job_id"]


def test_tiny_rounding_still_counts_as_same_box(client):
    first = client.post("/api/analyze", json=BOX).json()
    nearly = {k: v + 0.00001 for k, v in BOX.items()}
    assert client.post("/api/analyze", json=nearly).json()["job_id"] == first["job_id"]


def test_different_box_gets_a_new_job(client):
    first = client.post("/api/analyze", json=BOX).json()
    other = dict(BOX, east=85.81)
    assert client.post("/api/analyze", json=other).json()["job_id"] != first["job_id"]


# ---------- Week 3: zones as a CSV file ----------

def test_zones_csv(client):
    zone = {"type": "Feature", "geometry": None, "properties": {
        "rank": 1, "tier_label": "Highest", "lat": 20.05, "lon": 85.05, "delta_t_c": 1.2,
        "lst_now_c": 40.1, "lst_after_c": 38.9, "tree_pct_now": 5, "tree_pct_after": 25,
        "built_pct": 60, "canopy_added_m2": 2000, "trees_est": 40}}
    (main.DATA_ROOT / "testville" / "priority.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": [zone]}))
    r = client.get("/api/priority/testville/zones.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "testville_zones.csv" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("rank,tier_label,lat,lon") and len(lines) == 2
    assert lines[1].startswith("1,Highest,20.05,85.05")


def test_zones_csv_old_file_without_canopy(client):
    zone = {"type": "Feature", "geometry": None, "properties": {"rank": 1, "tier_label": "High"}}
    (main.DATA_ROOT / "testville" / "priority.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": [zone]}))
    assert client.get("/api/priority/testville/zones.csv").text.splitlines()[1].startswith("1,High,")


def test_zones_csv_missing_area(client):
    assert client.get("/api/priority/nowhere/zones.csv").status_code == 404
    assert client.get("/api/priority/Bad_Slug/zones.csv").status_code == 400


# ---------- one block anywhere ----------

GRID_HEADER = "row,col,west,east,north,south,water_frac,tree_frac,grass_frac,crops_frac,shrub_frac,built_frac,bare_frac,ndvi_mean,lst_mean,lon,lat,added,delta_t,eligible,rank,tier,canopy_added_m2,trees_est\n"


def write_grid(rows):
    (main.DATA_ROOT / "testville" / "grid_features.csv").write_text(GRID_HEADER + "".join(rows))
    main._grid_cache.clear()


def test_cell_eligible_block(client):
    write_grid(["0,0,85.0,85.001,20.1,20.099,0,0.1,0,0.3,0,0.6,0,0.2,41.0,85.0005,20.0995,0.2,2.5,True,7,1,1860,37\n",
                "0,1,85.001,85.002,20.1,20.099,0.6,0,0,0,0,0,0.4,0.1,33.0,85.0015,20.0995,0,0.1,False,0,0,0,0\n"])
    r = client.get("/api/cell/testville", params={"lat": 20.0996, "lon": 85.0004}).json()
    assert r["eligible"] and r["rank"] == 7 and r["ranked_blocks"] == 1
    assert r["delta_t_c"] == 2.5 and r["lst_after_c"] == 38.5 and r["tree_pct_after"] == 30
    assert r["land_pct"]["built"] == 60 and r["trees_est"] == 37


def test_cell_not_eligible_says_why(client):
    write_grid(["0,1,85.001,85.002,20.1,20.099,0.6,0,0,0,0,0,0.4,0.1,33.0,85.0015,20.0995,0,0.1,False,0,0,0,0\n"])
    r = client.get("/api/cell/testville", params={"lat": 20.0996, "lon": 85.0014}).json()
    assert r["eligible"] is False and r["reason"] == "Mostly water" and r["delta_t_c"] is None


def test_cell_outside_or_missing(client):
    write_grid(["0,0,85.0,85.001,20.1,20.099,0,0.1,0,0.3,0,0.6,0,0.2,41.0,85.0005,20.0995,0.2,2.5,True,7,1,1860,37\n"])
    assert client.get("/api/cell/testville", params={"lat": 20.05, "lon": 85.05}).status_code == 404
    assert client.get("/api/cell/nowhere", params={"lat": 21.05, "lon": 86.05}).status_code == 404
    assert client.get("/api/cell/Bad_Slug", params={"lat": 21.05, "lon": 86.05}).status_code == 400
