'''One-time migration of the shipped history CSVs to the new formats.

Runs the project's own jobs_logger migration on the real files:
- failed CSV gains Title/Company columns
- genuine-failure counts are recomputed with skip-noise excluded
- a skipped-jobs CSV is initialized from the historical skip rows
'''

import sys
import os
from pathlib import Path

PROJECT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, PROJECT)
os.chdir(PROJECT)  # history CSV paths in settings.py are relative

import csv
from collections import Counter

import modules.jobs_logger as jl

# 1) Migrate the failed CSV in place (adds Title/Company, preserves rows)
jl._ensure_failed_header()

rows = list(csv.DictReader(open(jl.failed_file_name, encoding="utf-8-sig", newline="")))
print(f"failed CSV: {len(rows)} rows, header now: {'Title' in rows[0]}, Company: {'Company' in rows[0]}")

# 2) Genuine failure counts vs skip noise
genuine = [r for r in rows if r.get("Assumed Reason") not in jl.SKIP_REASON_VALUES and r.get("External Job link") != "Skipped"]
noise = len(rows) - len(genuine)
print(f"genuine failures: {len(genuine)} | historical skip-noise rows: {noise}")

top = Counter(r["Job ID"] for r in genuine).most_common(5)
print("most-retried genuine failures:", [(jid[:50], c) for jid, c in top])

# 3) Seed the skipped-jobs CSV from the historical skip rows so the new
#    dashboard Skipped tab has data from day one.
skipped_rows = [r for r in rows if r.get("Assumed Reason") in jl.SKIP_REASON_VALUES or r.get("External Job link") == "Skipped"]
seen = set()
written = 0
for r in skipped_rows:
    jid = r.get("Job ID", "")
    if not jid or jid in seen:
        continue
    seen.add(jid)
    jl.skipped_job(
        "Naukri", jid, "", r.get("Company", ""), "", "", r.get("Search Term", ""),
        r.get("Assumed Reason", ""), r.get("Stack Trace", ""), r.get("Job Link", ""),
    )
    written += 1
print(f"skipped CSV seeded with {written} unique historically-skipped jobs")

# 4) Recount for the final report
counts = jl.get_failed_job_counts("Naukri")
print("jobs over retry limit 2:", sum(1 for c in counts.values() if c >= 2))
