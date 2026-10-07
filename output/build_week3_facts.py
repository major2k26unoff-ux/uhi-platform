"""Rebuild the Track 1 facts PDF from code and saved measurement files."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import math
from html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "output" / "pdf"
OUT.mkdir(parents=True, exist_ok=True)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CellSmall", fontName="Helvetica", fontSize=7, leading=10))
styles.add(ParagraphStyle(name="Evidence", fontName="Helvetica", fontSize=8, leading=11, textColor=colors.HexColor("#52636b")))
story = []
WIDTH = landscape(A4)[0] - 84


def text(value, style="BodyText"):
    story.append(Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style]))
    story.append(Spacer(1, 7))


def section(number, title):
    story.append(Paragraph(f"{number}. {escape(title)}", styles["Heading1"]))


def source(path):
    full = ROOT / path
    if full.exists():
        stamp = datetime.fromtimestamp(full.stat().st_mtime, ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST")
        text(f"Source: {path}; file modified {stamp}.", "Evidence")
    else:
        text(f"Source: {path}; not measured (file absent).", "Evidence")


def table(rows, widths=None):
    cells = [[Paragraph(escape(str(v)), styles["CellSmall"]) for v in row] for row in rows]
    t = Table(cells, colWidths=widths or [WIDTH / len(rows[0])] * len(rows[0]), repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d8eee8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7f8")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c4d2d8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([t, Spacer(1, 10)])


def markdown(path):
    p = ROOT / path
    if not p.exists():
        text("Not measured: this result file does not yet exist.")
        source(path)
        return
    block = []
    def flush():
        if not block:
            return
        if len(block[0]) > 9:
            # Preserve every column in two tables with repeated city labels.
            mid = 8
            table([r[:mid] for r in block])
            story.append(PageBreak())
            table([[r[0]] + r[mid:] for r in block])
        else:
            table(block)
        block.clear()
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("|"):
            row = [v.strip() for v in line.strip().strip("|").split("|")]
            if all(v and set(v) <= set("-: ") for v in row):
                continue
            block.append(row)
        else:
            flush()
            if line.strip():
                text(line)
    flush()
    source(path)


def photo(path, caption):
    p = ROOT / path
    if not p.exists():
        text(f"Not measured / image absent: {path}")
        return
    image = Image(str(p))
    factor = min(350 / image.imageWidth, 290 / image.imageHeight)
    image.drawWidth, image.drawHeight = image.imageWidth * factor, image.imageHeight * factor
    story.append(KeepTogether([image, Spacer(1, 8), Paragraph(escape(caption), styles["BodyText"]), Paragraph(escape(f"Source: {path}. Original PNG embedded without resampling."), styles["Evidence"])]))
    story.append(Spacer(1, 12))


def footer(canvas, doc):
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#52636b"))
    canvas.drawString(42, 22, "UHI platform | Track 1 | measured files and implementation facts")
    canvas.drawRightString(landscape(A4)[0] - 42, 22, str(doc.page))


date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %B %Y")
text(f"Facts - Track 1 - Track 1 - {date}", "Title")
text("Satellite data pipeline and worker", "Heading1")
text("Urban Heat Island & Green Canopy Analysis Platform. Local validation facts for the Week 3 handover. Author label supplied by the user: Track 1.")
runfile = DATA / "week3_run.json"
run = json.loads(runfile.read_text()) if runfile.exists() else {}
text("Run status: " + ("local satellite validation finished." if run.get("finished_at") else "validation is in progress; unfinished results are not measured."))
text("The human handover, video, Drive upload and delivery to Track 2 are pending. This PDF does not certify those activities.")
source("data/week3_run.json")
story.append(PageBreak())

section(1, "Data sources and bands")
table([["Layer / purpose", "Dataset", "Bands"],
       ["Satellite RGB", "COPERNICUS/S2_SR_HARMONIZED", "B4, B3, B2"],
       ["Cloud score", "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED", "cs_cdf"],
       ["NDVI", "Sentinel-2 surface reflectance", "B8 and B4"],
       ["NDBI", "Sentinel-2 surface reflectance", "B11 and B8"],
       ["NDWI", "Sentinel-2 surface reflectance", "B3 and B8"],
       ["Surface temperature", "LANDSAT/LC08/C02/T1_L2 and LANDSAT/LC09/C02/T1_L2", "ST_B10; QA_PIXEL for masking"]])
source("track1/pipeline.py")
section(2, "Dates")
table([["Source", "Start (inclusive)", "End (exclusive)"], ["Sentinel-2", "2024-03-01", "2024-05-31"], ["Landsat 8 and 9", "2024-03-01", "2024-06-15"]])
text("These configured historical windows target the pre-monsoon season. The code does not measure which months are the hottest or clearest in each city.")
source("track1/pipeline.py")
section(3, "Cloud masking")
text("Sentinel-2 is linked with Cloud Score+; pixels require cs_cdf >= 0.60, reflectance is divided by 10000, then a temporal median is used. Landsat requires L2SP and scene CLOUD_COVER < 40; QA_PIXEL cloud bit 3 and shadow bit 4 are masked before the median. Remaining cloud contamination has not been measured.")
source("track1/pipeline.py")
section(4, "Formulas")
table([["Layer", "Expression in code"], ["NDVI", "(B8 - B4) / (B8 + B4)"], ["NDBI", "(B11 - B8) / (B11 + B8)"], ["NDWI", "(B3 - B8) / (B3 + B8)"], ["LST in Celsius", "ST_B10 * 0.00341802 + 149.0 - 273.15"]])
source("track1/pipeline.py")
story.append(PageBreak())
section(5, "Export and alignment")
text("The pipeline chooses 10, 20, 25 or 50 m using an estimated 2500-pixel maximum side budget. Exports use EPSG:4326. All five layers must share CRS, transform, width and height. A temporary TIFF is validated before replacing the destination; each download gets up to three attempts. Previews have at most 1600 pixels on their longest side. Native thermal detail is approximately 100 m, regardless of export spacing; B11 is a 20 m optical band.")
text("The scale budget is a geographic estimate, not an assertion that every returned raster dimension is <= 2500. Preview LST colours use 25-45 C; values above 45 C saturate visually while the TIFF values remain intact.")
source("track1/pipeline.py")
section(6, "Worker and failure messages")
text("Requests and statuses live in data/jobs/<id>.request.json and <id>.status.json. One worker processes jobs oldest first, using each track's own virtual environment. Track 1 contributes 0-55% progress and Track 2 55-100%. Both must finish for status done. Startup requeues interrupted running jobs. Failed statuses retain a plain error and the last 1500 characters of error_detail; full child output remains in the terminal or captured validation log.")
text("The known tiny-area error is mapped to: This area is too small or too cloudy to rank planting zones. Draw a bigger box. The fallback for unknown errors directs the operator to the worker window.")
source("track1/worker.py")
story.append(PageBreak())
section(7, "Quality table: all preset cities")
markdown("data/quality_table.md")
text("Read the Valid LST and Valid NDVI columns as finite saved pixel coverage. The percentages are rounded to one decimal: 100.0% can still include a few masked pixels. They say nothing about the share of clear acquisition dates. The quality script's 'Problems found: none' covers missing expected TIFFs and low finite LST coverage; it is not a scientific accuracy verdict.")
story.append(PageBreak())
section(8, "Independent MODIS comparison")
markdown("data/modis_check.md")
modis_path = DATA / "modis_check.md"
if modis_path.exists():
    records = []
    for line in modis_path.read_text().splitlines():
        if line.startswith("|"):
            row = [v.strip() for v in line.strip("|").split("|")]
            try:
                records.append((row[0], float(row[3])))
            except (ValueError, IndexError):
                pass
    if records:
        biggest = max(records, key=lambda r: abs(r[1]))
        smallest = min(records, key=lambda r: abs(r[1]))
        text(f"Largest absolute offset: {biggest[0]} ({biggest[1]:+.1f} C). Smallest absolute offset: {smallest[0]} ({smallest[1]:+.1f} C). Differences in sea/land mixture, coarse spatial support, temporal compositing and clear-scene sampling are plausible explanations, not established causes. The observed offsets vary across cities; no constant bias correction has been validated.")
text("This compares stored Landsat city means against MOD11A2 daytime 8-day composite means. It does not match individual overpasses, apply additional MODIS QC bits, harmonize masks, or estimate Landsat accuracy. Composites selected by start date can overlap the window boundaries. The image count is the number of date-selected composites, not the number with usable data at each city. Correlation uses rounded values; a high correlation does not remove the temperature bias.")
source("track1/modis_check.py")
section(9, "Stress test")
markdown("data/stress_test.md")
text("Both rounds use the Week 3 worker. Round 1 began before a repository fast-forward: its first three model subprocesses used b08c895; remaining jobs and all of round 2 use 6e09013. They are repeated operational tests, not measured before/after repair evidence. The PDF-provided Minutes column includes queue wait; isolated processing minutes appear in section 11. A tiny-box failure due to fewer than 200 usable model cells is an expected model limit.")
source("data/week3_run.json")
source("data/week3_code_versions.json")
story.append(PageBreak())
section(10, "Repeat test")
for slug in ("titlagarh", "phalodi"):
    markdown(f"data/repeat_{slug}.md")
text("The saved baseline is compared with an independent rerun. CRS, shape, transform and valid-pixel masks must match. Zero valid pixels are not measured. Identical and tiny-change verdicts follow the supplied numerical tolerance; they establish repeatability for this run, not accuracy.")
source("track1/repeat_check.py")
section(11, "Measured run times")
runtime = [["Area / round", "Box km (approx.)", "Pixel m", "Pipeline minutes", "Full processing minutes", "Queue-to-finish minutes"]]
for r in run.get("rounds", []):
    for job_id in r["job_ids"]:
        req = json.loads((DATA / "jobs" / f"{job_id}.request.json").read_text())
        status_path = DATA / "jobs" / f"{job_id}.status.json"
        status = json.loads(status_path.read_text()) if status_path.exists() else {}
        meta_path = DATA / req["slug"] / "meta.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        b = req["bbox"]
        size = f"{(b['east']-b['west'])*111*math.cos(math.radians((b['south']+b['north'])/2)):.1f} x {(b['north']-b['south'])*111:.1f}"
        sec = status.get("processing_seconds")
        elapsed = (datetime.fromisoformat(status["updated_at"]) - datetime.fromisoformat(req["created_at"])).total_seconds()/60 if status.get("status") in ("done", "failed") else None
        runtime.append([f"{req['kind']} / {r['round']}", size, meta.get("scale_m", "not measured"), "not measured separately", f"{sec/60:.2f}" if sec is not None else "not measured", f"{elapsed:.2f}" if elapsed is not None else "not measured"])
for item in run.get("repeat_runs", []):
    meta = json.loads((DATA / item["slug"] / "meta.json").read_text())
    south, west, north, east = meta["bounds"]
    size = f"{(east-west)*111*math.cos(math.radians((south+north)/2)):.1f} x {(north-south)*111:.1f}"
    runtime.append([item["slug"] + " rerun", size, meta["scale_m"], f"{item['pipeline_seconds']/60:.2f}", "not measured", "not applicable"])
table(runtime)
(DATA / "run_times.md").write_text("\n".join(["| " + " | ".join(map(str, row)) + " |" for row in [runtime[0], ["---"] * len(runtime[0])] + runtime[1:]]) + "\n\nSources: data/week3_run.json and matching data/jobs/*.request.json and *.status.json.\n", encoding="utf-8")
source("data/run_times.md")
source("data/week3_run.json")
text("Processing durations for failed jobs measure time until failure. Box dimensions use the same geographic approximation as stress_test.py; they are not surveyed distances. Timing sources: matching data/jobs/<id> request and status files, and the runner manifest.")
section(12, "Sizes and limits")
table([["Limit", "Value / qualification", "Code source"], ["Website size", "0.3 degrees per side", "track3/main.py"], ["Minimum model", "200 usable 100 m cells; practical box size depends on eligibility", "track2/priority.py"], ["Pixel scales", "10, 20, 25, 50 m", "track1/pipeline.py"], ["Export budget", "Estimated 2500 pixels per side", "track1/pipeline.py"], ["Preview budget", "1600 pixels longest side", "track1/pipeline.py"], ["Area rule", "Coordinate order, size, broad southwest-corner India bounds; no national polygon test", "track3/main.py"]])
source("track3/main.py")
source("track2/priority.py")
story.append(PageBreak())
section(13, "Sample layers")
for layer, caption in [("rgb", "Bhubaneswar: Sentinel-2 visible-band composite."), ("ndvi", "Bhubaneswar: NDVI vegetation index, colour range -0.2 to 0.8."), ("ndbi", "Bhubaneswar: NDBI built-up index, colour range -0.5 to 0.5."), ("ndwi", "Bhubaneswar: NDWI water index, colour range -0.3 to 0.5."), ("lst", "Bhubaneswar: Landsat surface temperature, colour range 25-45 C; this is not air temperature.")]:
    photo(f"data/bhubaneswar/preview/{layer}.png", caption)
    story.append(PageBreak())
for layer in ("rgb", "lst"):
    photo(f"data/phalodi/preview/{layer}.png", f"Phalodi, Rajasthan: {layer.upper()} layer. Heat colours saturate above 45 C.")
    story.append(PageBreak())
successful = []
for r in run.get("rounds", []):
    for job_id in r["job_ids"]:
        statuspath = DATA / "jobs" / f"{job_id}.status.json"
        if statuspath.exists() and json.loads(statuspath.read_text()).get("status") == "done":
            successful.append(json.loads((DATA / "jobs" / f"{job_id}.request.json").read_text()))
if successful:
    req = successful[0]
    photo(f"data/{req['slug']}/preview/lst.png", f"Successful real-system stress case: {req['display_name']}; Landsat surface-temperature preview.")
else:
    text("Successful stress-case image: not measured.")
story.append(PageBreak())
section(14, "Limits and handover status")
text("Surface temperature differs from air temperature. Resampling cannot create thermal detail. Cloud masking and median composites are imperfect. Fixed-date imagery does not represent current conditions. MODIS agreement in rank leaves substantial temperature offsets. Dry riverbeds and dense urban roofs can confuse planting eligibility; cooling scenarios need independent model and photo review. Finite data coverage does not establish cloud-free or uncontaminated observations.")
source("track1/README.md")
source("track2/results_week2.md")
text("The launcher and run_all.py are present after the Week 2 integration fast-forward; launcher and launcher-log checks on Track 2's machine remain pending. The Track 2 handover session, narrated video, Drive uploads and direct delivery have not been completed by this local validation. No completion is claimed for the other tracks' Week 3 tasks.")
text("The repeat checker was minimally strengthened to compare CRS and valid masks, distinguish empty comparisons, restrict slugs and preserve an existing baseline. Offline regression coverage includes worker error/detail persistence, restart recovery, repeated stress report retention, CRS differences, lost valid pixels and empty rasters.")
source("track1/test_week3.py")
source("data/week3_regression.txt")
text("No original PDF numbers were substituted for local measurements. Tables and images come from the named saved files; absent outputs are explicitly not measured. Existing output dates may differ from this PDF's build date.")

destination = OUT / "Facts_Track1_Track1.pdf"
SimpleDocTemplate(str(destination), pagesize=landscape(A4), rightMargin=42, leftMargin=42, topMargin=36, bottomMargin=38, title="Facts - Track 1", author="Track 1").build(story, onFirstPage=footer, onLaterPages=footer)
print(destination)
