"""Build study-app/courses.json from the gathered material in ../notebook-loads.

Run once (or again after adding courses):
    python study-app/tools/build_catalog.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
LOADS = APP.parents[1] / "notebook-loads"

# Plan order. "optional" courses are never picked automatically as the next course.
ORDER = [
    ("cs50p", "CS50P - Introduction to Programming with Python", "Stage 1", "2ab989ec-5498-499e-a93e-9fc98d7b8298", "cs50p.tsv", False),
    ("cs50ai", "CS50 AI - Introduction to AI with Python", "Stage 1.5", "5f35773b-6bbf-4051-9a20-efba0791561a", "cs50ai.tsv", False),
    ("ap03", None, "Stage 2", None, "03-ml.tsv", False),
    ("ap28", None, "Stage 2 depth (optional)", None, "28-cs229.tsv", True),
    ("ap04", None, "Stage 3", None, "04-dl.tsv", False),
    ("ap06", None, "Stage 4", None, "06", False),
    ("ap11", None, "Stage 4", None, "11", False),
    ("ap26", None, "Stage 4 (theory)", None, "26-cs224n.tsv", False),
    ("ap27", None, "Stage 4 (core)", None, "27-cs336.tsv", False),
    ("ap05", None, "Stage 5", None, "05-genai.tsv", False),
    ("ap12", None, "Stage 5", None, "12", False),
    ("ap13", None, "Stage 5", None, "13", False),
    ("ap07", None, "Stage 5", None, "07-agentic.tsv", False),
    ("ap10", None, "Stage 5", None, "10-mcp.tsv", False),
    ("ap09", None, "Stage 5", None, "09", False),
    ("ap14", None, "Stage 5", None, "14-fastapi.tsv", False),
    ("ap15", None, "Stage 5", None, "15", False),
    ("ap16", None, "Production", None, "16", False),
    ("ap17", None, "Production", None, "17", False),
    ("ap18", None, "Production", None, "18", False),
    ("ap19", None, "Production", None, "19", False),
    ("ap20", None, "Production", None, "20", False),
    ("ap21", None, "Production", None, "21", False),
    ("ap08", None, "Production", None, "08", False),
    ("ap22", None, "Career", None, "22", False),
    ("ap23", None, "Cloud (pick one)", None, "23", False),
    ("ap24", None, "Cloud (pick one)", None, "24", False),
    ("ap25", None, "Cloud (pick one)", None, "25", False),
    ("ap01", None, "Stage 1 backup (Hindi)", None, "01-python.tsv", True),
    ("ap02", None, "Optional side skill", None, "02", True),
]


def read_tsv(name):
    rows = []
    for line in (LOADS / name).read_text(encoding="utf-8-sig").splitlines():
        p = line.split("\t")
        if len(p) >= 3 and p[2].startswith("http"):
            dur = int(float(p[3])) if len(p) > 3 and re.fullmatch(r"[\d.]+", p[3] or "") else 0
            rows.append({"title": p[1], "url": p[2], "duration": dur})
    return rows


def youtube_id(url):
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
    return m.group(1) if m else None


def lookup(url):
    """Title and duration for a single video, via yt-dlp."""
    p = subprocess.run([sys.executable, "-m", "yt_dlp", "--skip-download", "--print",
                        "%(title)s\t%(duration)s", url], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    parts = p.stdout.strip().split("\t")
    if len(parts) == 2 and parts[1].replace(".", "").isdigit():
        return parts[0], int(float(parts[1]))
    return None, 0


playlists = json.loads((LOADS / "state.json").read_text())
singles = json.loads((LOADS / "singles-state.json").read_text())
by_key = {k.split("-")[0]: v for k, v in playlists.items()}  # "03" -> {...}

courses = []
for cid, title, stage, nb, src, optional in ORDER:
    num = cid[2:] if cid.startswith("ap") else None
    if src.endswith(".tsv"):
        items = read_tsv(src)
        if num:
            title, nb = by_key[num]["title"], by_key[num]["id"]
    else:
        s = singles[src]
        title, nb = s["title"], s["id"]
        if youtube_id(s["url"]):
            vt, dur = lookup(s["url"])
            items = [{"title": vt or title, "url": s["url"], "duration": dur}]
        else:
            items = [{"title": title.split(" - ", 1)[-1], "url": s["url"], "duration": 0}]
    for i, it in enumerate(items):
        it["id"] = f"{cid}-{i:03d}"
        it["youtube"] = youtube_id(it["url"])
        it["kind"] = "video" if it["youtube"] else "read"
    courses.append({"id": cid, "num": num, "title": title, "stage": stage,
                    "notebook": nb, "optional": optional, "items": items})
    print(f"{cid}: {len(items)} items", flush=True)

out = APP / "courses.json"
out.write_text(json.dumps({"courses": courses}, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"wrote {out} ({sum(len(c['items']) for c in courses)} items)")
