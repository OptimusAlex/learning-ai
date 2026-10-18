"""My AI Cohort: a local study app over the gathered courses and NotebookLM notebooks.

Run:  .venv\\Scripts\\python -m uvicorn app:app --app-dir study-app --port 8000
Data: progress/progress.json, progress/quiz-results.json, LEARNING.md (all inside the repo).
"""
import json
import re
import subprocess
import threading
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_DIR = Path(__file__).resolve().parent
REPO = APP_DIR.parent
PROGRESS_DIR = REPO / "progress"
PROGRESS = PROGRESS_DIR / "progress.json"
QUIZZES = PROGRESS_DIR / "quiz-results.json"
JOURNAL = REPO / "LEARNING.md"
TRACKER = REPO.parent / "AI-ENGINEER-RESOURCES.md"  # outside the repo, updated in place

CATALOG = json.loads((APP_DIR / "courses.json").read_text(encoding="utf-8"))["courses"]
COURSES = {c["id"]: c for c in CATALOG}
ITEMS = {it["id"]: (c, it) for c in CATALOG for it in c["items"]}

# Weekly rhythm from SCHEDULE.md (Mon=0).
DAY_PLAN = {
    0: ("Lecture day", "Watch the first half of the lecture. Type the code along."),
    1: ("Lecture day", "Finish the lecture. Pause, type, run, change something."),
    2: ("Practice day", "Start the problem set or rebuild today's examples yourself."),
    3: ("Practice + maths", "Keep practising. From week 5 add 3Blue1Brown maths."),
    4: ("Quiz + review", "Take the quiz, re-watch weak spots, write the journal."),
    5: ("Weekend build (3 h)", "Problem set or project work."),
    6: ("Weekend build (3 h)", "Finish the week, then press Finish for today to push."),
}

lock = threading.Lock()
app = FastAPI(title="My AI Cohort")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


# ---------- storage ----------

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, data):
    PROGRESS_DIR.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_progress():
    p = load(PROGRESS, {})
    p.setdefault("current_course", CATALOG[0]["id"])
    p.setdefault("selected_item", None)
    p.setdefault("items", {})
    p.setdefault("days", {})
    p.setdefault("courses", {})
    return p


def today():
    return date.today().isoformat()


def touch_day(p, seconds=0, item=None):
    d = p["days"].setdefault(today(), {"seconds": 0, "items": []})
    d["seconds"] += seconds
    if item and item not in d["items"]:
        d["items"].append(item)


# ---------- course logic ----------

def course_state(p, cid):
    c = COURSES[cid]
    done = sum(1 for it in c["items"] if p["items"].get(it["id"], {}).get("done"))
    meta = p["courses"].get(cid, {})
    status = ("Skipped" if meta.get("skipped") else "Done" if done == len(c["items"])
              else "In progress" if done or meta.get("started") else "Not started")
    return {"id": cid, "num": c["num"], "title": c["title"], "stage": c["stage"],
            "optional": c["optional"], "total": len(c["items"]), "done": done, "status": status}


def next_item(p, cid):
    for it in COURSES[cid]["items"]:
        if not p["items"].get(it["id"], {}).get("done"):
            return it
    return None


def advance_course(p):
    """If the current course is finished or skipped, move to the next non-optional one."""
    if course_state(p, p["current_course"])["status"] not in ("Done", "Skipped"):
        return
    for c in CATALOG:
        if not c["optional"] and course_state(p, c["id"])["status"] not in ("Done", "Skipped"):
            p["current_course"] = c["id"]
            p["selected_item"] = None
            return


def streak(p):
    active = {d for d, v in p["days"].items() if v.get("seconds", 0) > 0 or v.get("items")}
    day = date.today()
    if day.isoformat() not in active:
        day -= timedelta(days=1)
    n = 0
    while day.isoformat() in active:
        n += 1
        day -= timedelta(days=1)
    return n


def update_tracker(cid, p):
    """Write Status / Started / Finished for AI Path courses into AI-ENGINEER-RESOURCES.md."""
    c = COURSES[cid]
    if not c["num"] or not TRACKER.exists():
        return
    st = course_state(p, cid)
    meta = p["courses"].get(cid, {})
    lines = TRACKER.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        cells = line.split("|")
        # Tracker rows have 9 columns: | # | Resource | Type | Size | Stage | Status | Started | Finished | Notes |
        if len(cells) == 11 and cells[1].strip() == c["num"]:
            cells[6] = f" {st['status']} "
            cells[7] = f" {meta.get('started', '')} "
            cells[8] = f" {meta.get('finished', '')} "
            lines[i] = "|".join(cells)
            break
    TRACKER.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mark_started(p, cid):
    meta = p["courses"].setdefault(cid, {})
    if not meta.get("started"):
        meta["started"] = today()
        update_tracker(cid, p)


def item_view(p, it):
    if not it:
        return None
    s = p["items"].get(it["id"], {})
    return {**it, "position": s.get("position", 0), "done": s.get("done", False)}


# ---------- API ----------

@app.get("/")
def index():
    return FileResponse(APP_DIR / "static" / "index.html")


@app.get("/api/state")
def state():
    with lock:
        p = load_progress()
        advance_course(p)
        cid = p["current_course"]
        sel = p["selected_item"]
        it = ITEMS[sel][1] if sel in ITEMS and ITEMS[sel][0]["id"] == cid else next_item(p, cid)
        quizzes = load(QUIZZES, [])
        weak = {}
        for q in quizzes[-30:]:
            for t in q.get("wrong_topics", []):
                weak[t] = weak.get(t, 0) + 1
        label, hint = DAY_PLAN[date.today().weekday()]
        return {
            "today": today(), "day_label": label, "day_hint": hint,
            "streak": streak(p),
            "minutes_today": round(p["days"].get(today(), {}).get("seconds", 0) / 60),
            "current": course_state(p, cid) | {"notebook": COURSES[cid]["notebook"]},
            "item": item_view(p, it),
            "courses": [course_state(p, c["id"]) for c in CATALOG],
            "weak_topics": sorted(weak, key=weak.get, reverse=True)[:6],
            "recent_quizzes": quizzes[-5:][::-1],
            "days": {d: round(v.get("seconds", 0) / 60) for d, v in p["days"].items()},
        }


@app.get("/api/course/{cid}")
def course(cid: str):
    if cid not in COURSES:
        raise HTTPException(404)
    p = load_progress()
    return {"course": course_state(p, cid),
            "items": [item_view(p, it) for it in COURSES[cid]["items"]]}


class Select(BaseModel):
    course: str
    item: str | None = None


@app.post("/api/select")
def select(s: Select):
    if s.course not in COURSES or (s.item and s.item not in ITEMS):
        raise HTTPException(404)
    with lock:
        p = load_progress()
        p["current_course"] = s.course
        p["selected_item"] = s.item
        p["courses"].setdefault(s.course, {}).pop("skipped", None)
        save(PROGRESS, p)
    return {"ok": True}


class Progress(BaseModel):
    item: str
    position: float
    duration: float = 0
    delta: float = 0


@app.post("/api/progress")
def progress(b: Progress):
    if b.item not in ITEMS:
        raise HTTPException(404)
    c, it = ITEMS[b.item]
    with lock:
        p = load_progress()
        s = p["items"].setdefault(b.item, {})
        s["position"] = round(b.position)
        dur = b.duration or it["duration"]
        newly_done = False
        if dur and b.position >= 0.92 * dur and not s.get("done"):
            s["done"], s["done_on"], newly_done = True, today(), True
        touch_day(p, min(max(b.delta, 0), 15), b.item)
        mark_started(p, c["id"])
        if newly_done:
            finish_course_if_done(p, c["id"])
        save(PROGRESS, p)
    return {"done": s.get("done", False)}


def finish_course_if_done(p, cid):
    if course_state(p, cid)["status"] == "Done":
        p["courses"].setdefault(cid, {})["finished"] = today()
    update_tracker(cid, p)


class Complete(BaseModel):
    item: str
    done: bool = True


@app.post("/api/complete")
def complete(b: Complete):
    if b.item not in ITEMS:
        raise HTTPException(404)
    c, _ = ITEMS[b.item]
    with lock:
        p = load_progress()
        s = p["items"].setdefault(b.item, {})
        s["done"] = b.done
        s["done_on"] = today() if b.done else None
        if p["selected_item"] == b.item and b.done:
            p["selected_item"] = None  # move on to the next unwatched item
        touch_day(p, 0, b.item)
        mark_started(p, c["id"])
        finish_course_if_done(p, c["id"])
        save(PROGRESS, p)
    return {"ok": True}


class Skip(BaseModel):
    course: str


@app.post("/api/skip")
def skip(b: Skip):
    with lock:
        p = load_progress()
        p["courses"].setdefault(b.course, {})["skipped"] = True
        update_tracker(b.course, p)
        save(PROGRESS, p)
    return {"ok": True}


# ---------- quiz (NotebookLM via nlm) ----------

QUIZ_PROMPT = (
    'Make a quiz using ONLY the source titled "{title}".{focus} '
    "Write exactly 5 multiple-choice questions that test understanding, not trivia. "
    "Reply with ONLY a JSON object, no other text, in this shape: "
    '{{"questions":[{{"q":"question","options":["a","b","c","d"],"answer":0,'
    '"explain":"one or two sentences","topic":"2-4 word topic"}}]}} '
    "where answer is the 0-based index of the correct option."
)


def clean(s):
    return re.sub(r"\s*\[\d+(?:\s*[,-]\s*\d+)*\]", "", s).strip() if isinstance(s, str) else s


class QuizReq(BaseModel):
    item: str


@app.post("/api/quiz")
def quiz(b: QuizReq):
    if b.item not in ITEMS:
        raise HTTPException(404)
    c, it = ITEMS[b.item]
    pos = load_progress()["items"].get(b.item, {}).get("position", 0)
    focus = ""
    if it["duration"] and 0 < pos < 0.9 * it["duration"]:
        focus = (f" The learner has watched about the first {pos // 60} of "
                 f"{it['duration'] // 60} minutes, so focus on the earlier part.")
    prompt = QUIZ_PROMPT.format(title=it["title"], focus=focus)
    try:
        r = subprocess.run(["nlm", "notebook", "query", c["notebook"], prompt, "--json"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=240)
    except FileNotFoundError:
        raise HTTPException(500, "nlm is not installed or not on PATH.")
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "NotebookLM took too long. Try again.")
    out = r.stdout or ""
    if r.returncode != 0 or "{" not in out:
        msg = (out + r.stderr)[-300:]
        if "auth" in msg.lower() or "login" in msg.lower():
            msg = "NotebookLM login expired. Run  nlm login  in PowerShell, then try again."
        raise HTTPException(502, msg)
    try:
        answer = json.loads(out[out.index("{"):out.rindex("}") + 1])["answer"]
        answer = re.sub(r"```(?:json)?", "", answer)
        data = json.loads(answer[answer.index("{"):answer.rindex("}") + 1])
        qs = []
        for q in data["questions"]:
            opts = [clean(o) for o in q["options"]]
            a = int(q["answer"])
            if len(opts) >= 2 and 0 <= a < len(opts):
                qs.append({"q": clean(q["q"]), "options": opts, "answer": a,
                           "explain": clean(q.get("explain", "")),
                           "topic": clean(q.get("topic", "general"))})
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, "NotebookLM's reply was not a readable quiz. Try again.")
    if not qs:
        raise HTTPException(502, "No usable questions came back. Try again.")
    return {"item": b.item, "title": it["title"], "questions": qs}


class QuizResult(BaseModel):
    item: str
    score: int
    total: int
    wrong_topics: list[str] = []


@app.post("/api/quiz/result")
def quiz_result(b: QuizResult):
    if b.item not in ITEMS:
        raise HTTPException(404)
    c, it = ITEMS[b.item]
    with lock:
        qs = load(QUIZZES, [])
        qs.append({"date": today(), "course": c["id"], "item": b.item, "title": it["title"],
                   "score": b.score, "total": b.total, "wrong_topics": b.wrong_topics})
        save(QUIZZES, qs)
        p = load_progress()
        touch_day(p, 0, b.item)
        save(PROGRESS, p)
    return {"ok": True}


# ---------- journal and GitHub ----------

class Journal(BaseModel):
    did: str
    confused: str = ""
    next: str = ""


@app.post("/api/journal")
def journal(b: Journal):
    p = load_progress()
    it = item_view(p, ITEMS.get(p["selected_item"], (None, None))[1] or next_item(p, p["current_course"]))
    heading = f"## {today()} - {it['title'] if it else COURSES[p['current_course']]['title']}"
    entry = (f"\n{heading}\n\n- Did: {b.did.strip()}\n- Confused by: {b.confused.strip() or '-'}\n"
             f"- Next: {b.next.strip() or '-'}\n")
    with lock, JOURNAL.open("a", encoding="utf-8") as f:
        f.write(entry)
    return {"ok": True}


def git(*args):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


@app.post("/api/finish")
def finish():
    p = load_progress()
    d = p["days"].get(today(), {})
    titles = [ITEMS[i][1]["title"] for i in d.get("items", []) if i in ITEMS]
    qs = [q for q in load(QUIZZES, []) if q["date"] == today()]
    msg = f"{today()}: {round(d.get('seconds', 0) / 60)} min"
    if titles:
        msg += " - " + "; ".join(titles[:3]) + (" ..." if len(titles) > 3 else "")
    if qs:
        msg += f" - quiz {sum(q['score'] for q in qs)}/{sum(q['total'] for q in qs)}"
    log = []
    code, out = git("add", "-A")
    log.append(out)
    code, out = git("commit", "-m", msg)
    nothing = "nothing to commit" in out
    log.append(out)
    code, out = git("push")
    log.append(out)
    ok = code == 0
    return {"ok": ok, "committed": not nothing, "message": msg,
            "log": "\n".join(x for x in log if x)[-1500:]}
