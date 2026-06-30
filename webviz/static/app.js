const $ = (id) => document.getElementById(id);
const TOGGLES = ["multi", "retry", "max_iterations", "search"];
const TOGGLE_LESSON = { multi: "benchmark", retry: "retry-timeout",
  max_iterations: "max-iterations", search: "search-grounding" };
const SYSTEM_PROMPTS = {
  researcher: "You are a research specialist. Write concise numbered research notes.",
  analyst: "You are a critical analyst. Extract claims, compare views, flag weak evidence.",
  writer: "You are a technical writer. Write a cited, structured answer [N].",
  supervisor: "(supervisor không gọi LLM — chỉ định tuyến theo state.)",
};
let LESSONS = {};
let currentTab = "narr";

async function loadLessons() {
  const data = await (await fetch("/lessons")).json();
  data.forEach((l) => (LESSONS[l.id] = l));
}

function glossInline(text, glossary) {
  let out = text;
  glossary.forEach((g) => {
    const re = new RegExp(`\\b(${g.term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})\\b`);
    out = out.replace(re, `<span class="chip" title="${g.vi}">$1</span>`);
  });
  return out;
}

function setTab(tab) {
  currentTab = tab;
  $("tab-code").classList.toggle("active", tab === "code");
  $("tab-narr").classList.toggle("active", tab === "narr");
  $("lesson-code").classList.toggle("hidden", tab !== "code");
  $("lesson-narr").classList.toggle("hidden", tab !== "narr");
}
$("tab-code").onclick = () => setTab("code");
$("tab-narr").onclick = () => setTab("narr");

function showLesson(id, opt = {}) {
  const l = LESSONS[id];
  if (!l) return;
  $("lesson-title").textContent = l.title;
  $("code-a").textContent = `// ${l.option_a.label}  (${l.option_a.source_ref || "src"})\n${l.option_a.code}`;
  $("code-b").textContent = `// ${l.option_b.label}\n${l.option_b.code}`;
  $("narr-a").innerHTML = "<b>" + l.option_a.label + "</b><br>" + glossInline(l.option_a.narration, l.glossary);
  $("narr-b").innerHTML = "<b>" + l.option_b.label + "</b><br>" + glossInline(l.option_b.narration, l.glossary);
  $("glossary").innerHTML = l.glossary.map((g) => `<span class="gloss" title="${g.vi}">${g.term}: ${g.vi}</span>`).join("");
  if (opt.delta) { $("lesson-delta").textContent = opt.delta; $("lesson-delta").classList.remove("hidden"); }
  else { $("lesson-delta").classList.add("hidden"); }
  const dimA = opt.dimA === true;
  $("narr-a").classList.toggle("dim", dimA);
  $("code-a").parentElement.classList.toggle("dim", dimA);
  $("narr-b").classList.toggle("dim", !dimA);
  $("code-b").parentElement.classList.toggle("dim", !dimA);
  setTab(opt.openNarration ? "narr" : currentTab);
}

// REQUIRED: flipping ANY toggle instantly opens its lesson + the Thuyết minh tab + trước→sau, even before Run.
TOGGLES.forEach((name) => {
  $(`toggle-${name}`).addEventListener("change", (e) => {
    const on = e.target.checked;
    const after = {
      retry: on ? "1 lỗi mạng tạm thời sẽ được thử lại và workflow sống" : "1 lỗi mạng tạm thời sẽ làm chết cả workflow",
      search: on ? "có sources → trích dẫn được → coverage > 0" : "không sources → coverage = 0",
      max_iterations: on ? "có trần lặp, dừng an toàn" : "không trần → lặp đến khi backend chặn cứng ở 20",
      multi: on ? "chạy multi-agent có chuyên môn hóa" : "chỉ một lần gọi LLM (baseline)",
    }[name];
    showLesson(TOGGLE_LESSON[name], { openNarration: true, dimA: !on,
      delta: `${name}: ${on ? "TẮT → BẬT" : "BẬT → TẮT"} · giờ ${after}` });
  });
});

document.querySelectorAll("[data-lesson]").forEach((el) =>
  el.addEventListener("click", () => showLesson(el.dataset.lesson, { openNarration: true })));

function setBadges() {
  const live = $("mode-live").checked;
  $("badge-llm").textContent = "LLM: " + (live ? "OpenAI" : "Mock");
  $("badge-search").textContent = "Search: " + (live ? "Tavily" : "Mock");
  $("badge-llm").classList.toggle("live", live);
  $("badge-search").classList.toggle("live", live);
}
$("mode-live").addEventListener("change", setBadges);

$("break-tracing").addEventListener("click", () => {
  $("tracing-banner").classList.remove("hidden");
  showLesson("fail-open", { openNarration: true, delta: "tracing: vừa bị ép lỗi · workflow vẫn chạy (fail-open)" });
  runWorkflow({ break_tracing: true });
});

function readToggles() { const t = {}; TOGGLES.forEach((n) => (t[n] = $(`toggle-${n}`).checked)); return t; }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function applyEvent(ev) {
  if (ev.active_node) {
    document.querySelectorAll(".node").forEach((n) => n.classList.remove("active"));
    const node = $(`node-${ev.active_node}`); if (node) node.classList.add("active");
  }
  document.querySelectorAll(".edge").forEach((e) => e.classList.remove("active"));
  if (ev.edge_taken) {
    const e = document.querySelector(`[data-edge="${ev.edge_taken.source}-${ev.edge_taken.target}"]`);
    if (e) e.classList.add("active");
  }
  const s = ev.state_snapshot || {};
  [["sources", (s.sources && s.sources.length) ? `${s.sources.length} docs` : null],
   ["research_notes", s.research_notes], ["analysis_notes", s.analysis_notes],
   ["final_answer", s.final_answer]].forEach(([f, v]) => {
    const li = document.querySelector(`#state-fields li[data-field="${f}"]`);
    if (!li) return;
    li.classList.remove("read", "write");
    li.querySelector(".v").textContent = v ? "✔" : "None";
    li.classList.toggle("filled", !!v);
  });
  const WRITE = { researcher: ["sources", "research_notes"], analyst: ["analysis_notes"], writer: ["final_answer"] };
  const READ = { analyst: ["research_notes"], writer: ["research_notes", "analysis_notes", "sources"] };
  (WRITE[ev.active_node] || []).forEach((f) => document.querySelector(`li[data-field="${f}"]`)?.classList.add("write"));
  (READ[ev.active_node] || []).forEach((f) => document.querySelector(`li[data-field="${f}"]`)?.classList.add("read"));

  const c = (ev.lane && ev.lane.control) || {};
  $("lane-control").textContent = `route_history=[${(c.route_history || []).join(",")}] · iter=${c.iteration ?? 0}`;
  const o = (ev.lane && ev.lane.observability) || {};
  $("lane-obs").textContent = `trace: ${(o.trace || []).length}`;
  if (c.route_history && c.route_history.length) {
    const last = c.route_history[c.route_history.length - 1];
    $("decision-box").textContent = `Decision: iter ${c.iteration} → chọn ${last}`;
  }
  if (WRITE[ev.active_node]) { $("hat").classList.remove("hidden"); $("hat-text").textContent = SYSTEM_PROMPTS[ev.active_node] || ""; }

  const m = ev.metrics || {};
  if (m.citation_coverage != null) $("bar-cov").style.width = (m.citation_coverage * 100) + "%";
  if (m.estimated_cost_usd != null) $("bar-cost").style.width = Math.min(100, m.estimated_cost_usd * 1e5) + "%";

  const li = document.createElement("li");
  li.textContent = `[${ev.kind}] ${ev.note}`;
  if (ev.kind === "error") li.style.color = "#f85149";
  if (ev.kind === "warning") li.style.color = "#d29922";
  $("trace-list").appendChild(li);
}

async function runWorkflow(opts = {}) {
  $("trace-list").innerHTML = "";
  setBadges();
  const query = $("query").value;
  const toggles = readToggles();
  const body = { query, live: $("mode-live").checked, break_tracing: opts.break_tracing || false, toggles };
  const resp = await fetch("/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  const speed = () => parseInt($("speed").value, 10);
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let m;
    // SSE frames are separated by a blank line; sse-starlette uses CRLF (\r\n\r\n),
    // so match \r?\n\r?\n rather than only "\n\n" (the latter never matched → no render).
    while ((m = buf.match(/\r?\n\r?\n/))) {
      const frame = buf.slice(0, m.index); buf = buf.slice(m.index + m[0].length);
      const line = frame.split(/\r?\n/).find((l) => l.startsWith("data:"));
      if (!line) continue;
      const ev = JSON.parse(line.slice(5).trim());
      applyEvent(ev);
      await sleep(speed());
    }
  }
  try {
    const cmp = await (await fetch("/compare", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, toggles }) })).json();
    const single = cmp.single, multi = cmp.multi;
    const maxLat = Math.max(single.latency_seconds, multi.latency_seconds);
    $("bar-single").style.width = (maxLat ? single.latency_seconds / maxLat * 100 : 0) + "%";
    $("bar-multi").style.width = (maxLat ? multi.latency_seconds / maxLat * 100 : 0) + "%";
    if ($("label-single")) $("label-single").textContent = `single (cov ${single.citation_coverage}, ${single.agents} agent${single.agents !== 1 ? "s" : ""})`;
    if ($("label-multi")) $("label-multi").textContent = `multi (cov ${multi.citation_coverage}, ${multi.agents} agent${multi.agents !== 1 ? "s" : ""})`;
  } catch (_) {}
}

$("run").addEventListener("click", () => runWorkflow());

$("export-report").addEventListener("click", async () => {
  const body = { query: $("query").value, toggles: readToggles() };
  const md = await (await fetch("/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })).text();
  const blob = new Blob([md], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "benchmark_report.md"; a.click();
  URL.revokeObjectURL(a.href);
});

loadLessons().then(() => { setBadges(); showLesson("abstraction", { openNarration: true }); });
