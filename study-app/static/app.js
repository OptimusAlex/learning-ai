// My AI Cohort front end: today card, YouTube player with resume, quiz, journal, courses.
const $ = (id) => document.getElementById(id);
let S = null;            // last /api/state
let player = null;       // YT.Player
let ytReady = false;
let started = false;
let tick = null, lastTick = 0;
let courseItems = [];    // items of the current course
let showOptional = false;

window.onYouTubeIframeAPIReady = () => { ytReady = true; };

async function api(path, body) {
  const opt = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  };
  const r = await fetch(path, opt);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `Request failed (${r.status})`);
  return data;
}

function fmt(sec) {
  sec = Math.max(0, Math.round(sec || 0));
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  return (h ? `${h}:${String(m).padStart(2, "0")}` : `${m}`) + `:${String(s).padStart(2, "0")}`;
}

function toast(msg, ms = 4000) {
  const t = $("toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast.h);
  if (ms) toast.h = setTimeout(() => (t.hidden = true), ms);
}

// ---------- rendering ----------

async function refresh() {
  S = await api("/api/state");
  const it = S.item;
  $("streak").textContent = `🔥 ${S.streak} day${S.streak === 1 ? "" : "s"}`;
  $("minutes").textContent = `⏱ ${S.minutes_today} min today`;
  $("date").textContent = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "short" });
  $("day-label").textContent = S.day_label;
  $("day-hint").textContent = S.day_hint;
  $("course-title").textContent = `${S.current.num ? "AI Path " + S.current.num + " · " : ""}${S.current.title}`;
  if (it) {
    $("item-title").textContent = it.title;
    $("item-pos").textContent = it.kind === "video"
      ? (it.done ? "Watched ✓" : it.position ? `Resume at ${fmt(it.position)} of ${fmt(it.duration)}` : `Length ${fmt(it.duration)}`)
      : (it.done ? "Read ✓" : "Article");
  } else {
    $("item-title").textContent = "Course complete 🎉";
    $("item-pos").textContent = "Pick the next course below.";
  }
  $("mark").textContent = it && it.done ? "↺ Mark not done" : "✓ Mark done";
  courseItems = (await api(`/api/course/${S.current.id}`)).items;
  renderCurrent(); renderCourses(); renderHeat();
}

function renderCurrent() {
  const c = S.current;
  $("current").innerHTML = `<div><b>${c.num ? "AI Path " + c.num + " · " : ""}${esc(c.title)}</b></div>
    <div class="meta">${esc(c.stage)} · ${c.done}/${c.total} done · ${c.status}</div>
    <div class="bar"><i style="width:${(100 * c.done / c.total).toFixed(1)}%"></i></div>`;
  $("weak").innerHTML = S.weak_topics.length
    ? S.weak_topics.map((t) => `<span class="chip">${esc(t)}</span>`).join("")
    : `<li class="meta">None yet. Take a quiz.</li>`;
  $("recent").innerHTML = S.recent_quizzes.length
    ? S.recent_quizzes.map((q) => `<li>${q.date} · <b>${q.score}/${q.total}</b> · ${esc(q.title)}</li>`).join("")
    : `<li class="meta">No quizzes yet.</li>`;
}

function renderCourses() {
  $("courses").innerHTML = S.courses.filter((c) => showOptional || !c.optional).map((c) => `
    <li data-c="${c.id}" class="${c.id === S.current.id ? "active" : ""}">
      <div class="top"><span class="num">${c.num ? "AP " + c.num : c.id === "cs50p" ? "CS50P" : "CS50AI"}</span>
        <span>${esc(c.title.replace(/^AI Path \d+ - /, ""))}</span>
        <span class="status">${c.status} · ${c.done}/${c.total}</span></div>
      <div class="bar"><i style="width:${(100 * c.done / c.total).toFixed(1)}%"></i></div>
    </li>`).join("");
  document.querySelectorAll("#courses li").forEach((li) => li.onclick = () => openCourse(li.dataset.c));
}

function renderHeat() {
  const cells = [];
  for (let i = 27; i >= 0; i--) {
    const d = new Date(); d.setDate(d.getDate() - i);
    const key = d.toLocaleDateString("en-CA");  // YYYY-MM-DD in local time
    const m = S.days[key] || 0;
    const l = m === 0 ? "" : m < 20 ? "l1" : m < 60 ? "l2" : "l3";
    cells.push(`<i class="${l}" title="${key}: ${m} min"></i>`);
  }
  $("heat").innerHTML = cells.join("");
}

function esc(s) { return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

// ---------- player ----------

function startItem() {
  const it = S.item;
  if (!it) return;
  started = true;
  $("start-wrap").hidden = true;
  $("embed-error").hidden = true;
  if (it.kind === "read") {
    stopTick();
    $("player-wrap").hidden = true;
    $("read-wrap").hidden = false;
    $("read-link").href = it.url;
    return;
  }
  $("read-wrap").hidden = true;
  $("player-wrap").hidden = false;
  $("yt-link").href = `https://www.youtube.com/watch?v=${it.youtube}&t=${Math.round(it.position)}s`;
  const start = it.done ? 0 : Math.floor(it.position);
  if (player && player.loadVideoById) {
    player.loadVideoById({ videoId: it.youtube, startSeconds: start });
    return;
  }
  if (!ytReady) { setTimeout(startItem, 300); return; }
  player = new YT.Player("player", {
    videoId: it.youtube,
    playerVars: { start, rel: 0, modestbranding: 1, autoplay: 1 },
    events: {
      onStateChange: (e) => (e.data === YT.PlayerState.PLAYING ? startTick() : (sendProgress(), stopTick())),
      onError: () => { $("embed-error").hidden = false; },
    },
  });
}

function startTick() {
  if (tick) return;
  lastTick = Date.now();
  tick = setInterval(sendProgress, 5000);
}

function stopTick() { clearInterval(tick); tick = null; }

async function sendProgress(beacon = false) {
  if (!player || !player.getCurrentTime || !S.item || S.item.kind !== "video") return;
  const now = Date.now();
  const playing = tick && player.getPlayerState && player.getPlayerState() === YT.PlayerState.PLAYING;
  const delta = playing ? (now - lastTick) / 1000 : 0;
  lastTick = now;
  const body = { item: S.item.id, position: player.getCurrentTime(), duration: player.getDuration() || 0, delta };
  if (beacon) {
    navigator.sendBeacon("/api/progress", new Blob([JSON.stringify(body)], { type: "application/json" }));
    return;
  }
  try {
    const r = await api("/api/progress", body);
    S.item.position = body.position;
    $("item-pos").textContent = `At ${fmt(body.position)} of ${fmt(body.duration)}` + (r.done ? " · watched ✓" : "");
    $("minutes").textContent = `⏱ ${S.minutes_today + Math.round((delta) / 60)} min today`;
    if (r.done && !S.item.done) { S.item.done = true; toast("Video watched ✓. Take the quiz while it's fresh."); }
  } catch (e) { /* server busy; next tick retries */ }
}

window.addEventListener("beforeunload", () => sendProgress(true));

async function go(offset) {
  const idx = courseItems.findIndex((x) => S.item && x.id === S.item.id);
  const target = courseItems[idx + offset];
  if (!target) { toast(offset > 0 ? "That's the last item in this course." : "That's the first item."); return; }
  await sendProgress();
  await api("/api/select", { course: S.current.id, item: target.id });
  await refresh();
  if (started) startItem();
}

// ---------- quiz ----------

async function startQuiz() {
  if (!S.item) return;
  await sendProgress();
  $("quiz").hidden = false;
  $("quiz").scrollIntoView({ behavior: "smooth" });
  $("quiz-body").innerHTML = `<p class="meta">Asking NotebookLM for 5 questions on "${esc(S.item.title)}"… this can take up to a minute.</p>`;
  let data;
  try { data = await api("/api/quiz", { item: S.item.id }); }
  catch (e) { $("quiz-body").innerHTML = `<p class="note">${esc(e.message)}</p>`; return; }
  const answered = new Array(data.questions.length).fill(null);
  $("quiz-body").innerHTML = data.questions.map((q, i) => `
    <div class="q" data-i="${i}"><b>${i + 1}. ${esc(q.q)}</b>
      <div class="opts">${q.options.map((o, j) => `<button data-j="${j}">${String.fromCharCode(65 + j)}. ${esc(o)}</button>`).join("")}</div>
      <div class="explain" hidden></div></div>`).join("") + `<div class="score" id="quiz-score"></div>`;
  document.querySelectorAll(".q").forEach((div) => {
    const i = +div.dataset.i, q = data.questions[i];
    div.querySelectorAll("button").forEach((b) => b.onclick = async () => {
      if (answered[i] !== null) return;
      const j = +b.dataset.j;
      answered[i] = j;
      div.querySelectorAll("button").forEach((x) => (x.disabled = true));
      div.querySelector(`[data-j="${q.answer}"]`).classList.add("right");
      if (j !== q.answer) b.classList.add("wrong");
      const ex = div.querySelector(".explain");
      ex.textContent = (j === q.answer ? "✓ Correct. " : "✗ Not quite. ") + q.explain;
      ex.hidden = false;
      if (answered.every((a) => a !== null)) {
        const score = answered.filter((a, k) => a === data.questions[k].answer).length;
        const wrong = data.questions.filter((qq, k) => answered[k] !== qq.answer).map((qq) => qq.topic);
        $("quiz-score").textContent = `Score: ${score}/${data.questions.length}` + (wrong.length ? ` · review: ${wrong.join(", ")}` : " · perfect!");
        await api("/api/quiz/result", { item: data.item, score, total: data.questions.length, wrong_topics: wrong });
        refresh();
      }
    });
  });
}

// ---------- courses panel ----------

async function openCourse(cid) {
  const data = await api(`/api/course/${cid}`);
  $("items").hidden = false;
  $("items").dataset.c = cid;
  $("items-title").textContent = data.course.title;
  $("items-list").innerHTML = data.items.map((it) => `
    <li data-i="${it.id}" class="${it.done ? "done" : ""}">${esc(it.title)}
      <span class="meta">${it.kind === "video" ? fmt(it.duration) : "article"}${it.position && !it.done ? " · at " + fmt(it.position) : ""}</span></li>`).join("");
  document.querySelectorAll("#items-list li").forEach((li) => li.onclick = async () => {
    await sendProgress();
    await api("/api/select", { course: cid, item: li.dataset.i });
    $("items").hidden = true;
    await refresh();
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (started) startItem();
  });
  $("items").scrollIntoView({ behavior: "smooth" });
}

// ---------- wiring ----------

$("start").onclick = startItem;
$("prev").onclick = () => go(-1);
$("next").onclick = () => go(1);
$("mark").onclick = async () => {
  if (!S.item) return;
  await api("/api/complete", { item: S.item.id, done: !S.item.done });
  const wasDone = S.item.done;
  await refresh();
  if (!wasDone) toast("Marked done ✓");
  if (started && !wasDone) startItem();
};
$("quiz-btn").onclick = startQuiz;
$("quiz-close").onclick = () => ($("quiz").hidden = true);
$("journal-btn").onclick = () => { $("journal").hidden = false; $("journal").scrollIntoView({ behavior: "smooth" }); };
$("journal-close").onclick = () => ($("journal").hidden = true);
$("j-save").onclick = async () => {
  const did = $("j-did").value.trim();
  if (!did) { toast("Write at least what you did."); return; }
  await api("/api/journal", { did, confused: $("j-confused").value, next: $("j-next").value });
  ["j-did", "j-confused", "j-next"].forEach((id) => ($(id).value = ""));
  $("journal").hidden = true;
  toast("Saved to LEARNING.md ✓");
};
$("finish-btn").onclick = async () => {
  await sendProgress();
  $("finish-btn").disabled = true;
  toast("Saving to GitHub…", 0);
  try {
    const r = await api("/api/finish", {});
    toast(r.ok ? `Pushed to GitHub ✓\n${r.message}` : `Push had a problem:\n${r.log}`, r.ok ? 6000 : 0);
  } catch (e) { toast(e.message, 0); }
  $("finish-btn").disabled = false;
};
$("items-close").onclick = () => ($("items").hidden = true);
$("skip-course").onclick = async () => {
  const cid = $("items").dataset.c;
  if (!confirm("Skip this course? You can come back to it any time.")) return;
  await api("/api/skip", { course: cid });
  $("items").hidden = true;
  refresh();
};
// Theme toggle: starts from the saved choice, else the system setting.
function isDark() {
  const t = document.documentElement.dataset.theme;
  return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}
function paintThemeButton() {
  $("theme").textContent = isDark() ? "☀️" : "🌙";
  $("theme").title = isDark() ? "Switch to light" : "Switch to dark";
}
$("theme").onclick = () => {
  const next = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) {}
  paintThemeButton();
};
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", paintThemeButton);
paintThemeButton();

$("show-optional").onchange = (e) => { showOptional = e.target.checked; renderCourses(); };

refresh().catch((e) => toast("Could not load: " + e.message, 0));
