# Thiết kế: `webviz` — Web GUI minh họa Lab 20 Multi-Agent

- **Ngày:** 2026-06-29
- **Trạng thái:** Đã duyệt thiết kế, chờ review spec → lập kế hoạch
- **Mục đích học:** Giúp người mới *thấy* luồng multi-agent chạy, *đọc* code tương ứng, và *hiểu* vì sao production chọn cách này.

## 1. Vấn đề & mục tiêu

Lab 20 đã code xong 7 phần nhưng người học chưa "ngấm" vì mọi thứ chạy ẩn trong terminal. Cần một công cụ trực quan:

1. Xem **shared state** ("tấm bìa kẹp") đầy dần theo thời gian thực.
2. Mỗi tính năng có một **công tắc bật/tắt** → thấy ngay "nếu không có thì hỏng thế nào".
3. Mỗi bài học kèm **code thật** + **thuyết minh** (ưu/nhược, vì sao production chọn) với thuật ngữ tiếng Anh được chú thích tiếng Việt.

**Không mục tiêu (YAGNI):** không sửa `src/` (bài nộp), không đụng `rebuild-practice/`, không auth, không lưu lịch sử chạy, không deploy.

## 2. Nguyên tắc nền (tham chiếu, không định nghĩa lại)

- Chạy **chính code thật** trong `src/multi_agent_research_lab` qua LangGraph `.stream()` — viz phản ánh đúng hành vi thật.
- **Mock mode mặc định** (deterministic, miễn phí, offline) + **Live mode** tùy chọn (OpenAI/Tavily thật).
- Mock đạt được bằng **monkeypatch** `LLMClient`/`SearchClient` trong tiến trình backend — `src/` giữ nguyên.

## 3. Kiến trúc

```
Browser (index.html + app.js + style.css, không build step)
   │  POST /run  {query, live, toggles}
   │  ◀── SSE stream: mỗi event = 1 bước (state snapshot)
   │  POST /report  → trả markdown benchmark_report
   ▼
FastAPI backend (webviz/)
   server.py     — routes: GET / , POST /run (SSE), POST /report
   scenarios.py  — biến toggles → cấu hình chạy (patch gì, runner nào)
   fakes.py      — FakeLLMClient / FakeSearchClient (deterministic, diễn được lỗi)
   stream.py     — chạy workflow.stream(), map mỗi node → event SSE
   lessons/      — nội dung bài học (code A, code B, thuyết minh, glossary)
   ▼
src/multi_agent_research_lab  ← CODE THẬT (chỉ đọc, không sửa)
   workflow.stream() nhả ResearchState sau mỗi node
```

## 4. Thành phần backend

### 4.1 `fakes.py`
- `FakeLLMClient.complete()` trả nội dung deterministic theo system prompt (nhận diện researcher/analyst/writer/baseline) + token/cost giả ổn định.
- `FakeSearchClient.search()` trả danh sách `SourceDocument` cố định.
- Cờ "diễn lỗi": ném exception ở lần gọi đầu (để minh họa retry), hoặc luôn ném (để minh họa không-retry/Search-chết).

### 4.2 `scenarios.py`
Nhận `toggles` → quyết định:
- `multi` on/off → chọn runner (multi-agent workflow vs baseline 1-call).
- `retry` off → monkeypatch để bỏ lớp `@retry` của `LLMClient` **và** bật cờ lỗi ở fake (LLM hồi phục nếu retry on; Search luôn chết vì không có retry).
- `max_iterations` off → đặt trần rất cao + fake khiến `final_answer` không được điền → minh họa vòng lặp; backend **chặn cứng ở 20** và phát cảnh báo.
- `search` off → tiêm `FakeSearchClient` trả `[]` → coverage 0.

### 4.3 `stream.py`
- Mock mode: monkeypatch service clients bằng fakes trước khi build workflow.
- Chạy `compiled.stream({"research_state": state})`; sau mỗi node, emit event:
  `{step, active_node, edge_taken, state_snapshot, metrics, lane:{control, observability}, note}`.
- Baseline: emit 2 event (start/done).
- Bao toàn bộ trong try/except → lỗi thật cũng thành event `error` để UI hiển thị (không sập server).

### 4.4 `lessons/`
Mỗi bài học = 1 file dữ liệu (JSON/YAML), khóa theo công tắc/khái niệm. Trường:
- `id`, `title`
- `option_a`: `{label, code, source_ref, narration}` (code = trích thật từ `src/`)
- `option_b`: `{label, code, narration}` (code = counterfactual tự soạn)
- `glossary`: `[{term, vi}]`

Backend phục vụ qua `GET /lessons` hoặc nhúng sẵn vào trang.

## 5. Frontend — Layout A (dashboard + panel bài học)

```
┌─ CONTROLS: query [Run] [Mock|Live] · ☑multi ☑retry ☑max_iter ☑search · [⚡gây lỗi tracing] ─┐
├───────────────┬─────────────────────┬───────────────────────────────────────┤
│ GRAPH         │ TẤM BÌA (state)     │ PANEL BÀI HỌC  [Code][Thuyết minh]    │
│ nodes sáng    │ ô đọc/ghi tô màu    │ (tự đổi theo công tắc đang xem)        │
│ edges animate │ badge provider      │ Code phương án đang xem (A hoặc B)     │
│ (đứt/liền)    │ decision box        │ Thuyết minh: ưu/nhược · vì sao prod    │
│               │ 2 làn control/obs   │ thuật ngữ: inline + hover glossary     │
├───────────────┴─────────────────────┤                                       │
│ TRACE log · METRICS (latency/cost/coverage) · [So sánh single vs multi] [Xuất report.md] │
└──────────────────────────────────────┴───────────────────────────────────────┘
```

### 5.1 Hành vi trực quan (map tới 7 phần)
- **Graph:** node đang chạy sáng; edge đang đi animate — edge từ Supervisor **nét đứt** (conditional), worker→Supervisor **nét liền** (loop-back). *(Phần 5)*
- **Tấm bìa:** mỗi field hiện trạng thái None→✔; khi agent chạy, ô ĐỌC (đầu vào) và ô GHI (đầu ra) tô màu khác nhau. *(Phần 4)*
- **Badge provider** cạnh node: "LLM: Mock/OpenAI", "Search: Mock/Tavily". *(Phần 1, 2)*
- **Decision box:** mỗi tick Supervisor hiện suy luận "iter N · field X=✔ Y=None → chọn Z". *(Phần 3)*
- **2 làn control/observability:** `route_history`/`iteration` (control, lái graph) tô khác `trace` (observability). *(Phần 3, 6)*
- **Panel "chiếc mũ":** khi worker chạy, hiện system prompt của nó. *(Phần 4)*
- **So sánh + bar + Xuất report.md:** chạy cả baseline & multi cạnh nhau; nút xuất gọi `render_markdown_report` thật. *(Phần 7)*
- **Nút "gây lỗi tracing":** ép lớp trace ném lỗi; workflow vẫn xong → banner fail-open. *(Phần 6)*

### 5.2 Panel bài học (tính năng mới)
- Hai tab: **Code** và **Thuyết minh**.
- **Tự đồng bộ với công tắc:** đang bật (phương án A) → hiện code+thuyết minh A; tắt (phương án B) → đổi sang B. Có thể xem code A/B đối chiếu (bản còn lại làm mờ).
- **Bấm công tắc = bật thuyết minh ngay (BẮT BUỘC):** mỗi lần gạt một công tắc, panel bài học **tự nhảy tới đúng bài học của công tắc đó** và **tự mở tab Thuyết minh**, hiển thị một dòng "trước → sau" tóm tắt hậu quả vừa thay đổi (vd: "retry: BẬT → TẮT · giờ 1 lỗi mạng tạm thời sẽ làm chết cả workflow"). Người học không phải tự đi tìm — gạt là hiểu liền. Việc này độc lập với nút [Run]: chỉ cần gạt công tắc đã thấy giải thích, chạy hay chưa cũng được.
- **Code thật** trích từ `src/` (có `source_ref` chỉ rõ file:dòng). **Code B** là bản counterfactual ngắn.
- **Thuyết minh:** ưu/nhược từng phương án + "vì sao production chọn A". Thuật ngữ tiếng Anh: chú thích tiếng Việt **inline** lần đầu + **chip hover** hiện lại định nghĩa + link tới **bảng glossary** chung.

## 6. Luồng dữ liệu (1 lần chạy)

1. User đặt query, chọn Mock/Live, gạt công tắc → `POST /run`.
2. `scenarios` dựng cấu hình; `stream` (mock) monkeypatch fakes, build workflow.
3. `workflow.stream()` chạy; mỗi node → 1 event SSE.
4. Frontend nhận event: sáng node + animate edge, điền ô tấm bìa, append trace, cập nhật metrics, đồng bộ panel bài học theo công tắc.
5. Có nút tốc độ (chậm/nhanh) để xem rõ từng bước.

## 7. Xử lý lỗi & an toàn

- Live thiếu API key → event `error` thân thiện, gợi tắt Live. Mock luôn chạy offline.
- Demo vòng lặp luôn có **trần cứng 20** dù tắt guardrail.
- Tracing best-effort: lỗi tracing không làm sập server (đúng tinh thần fail-open của `src/`).
- Backend bọc mọi lỗi runtime thành event, không để 500 làm đứng UI.

## 8. Kiểm thử (`tests/` cho webviz, không gọi mạng)

- `fakes` deterministic: cùng input → cùng output.
- `scenarios`: mỗi công tắc off tạo đúng cấu hình (vd search off → coverage 0; retry off + lỗi → LLM xong, Search lỗi).
- `stream`: số event = số node; baseline = 2 event; có event `error` khi ép lỗi.
- `lessons`: mỗi file có đủ trường; `source_ref` trỏ tới file `src/` tồn tại.
- Pytest, offline hoàn toàn.

## 9. Bố cục file & cách chạy

```
webviz/
  __init__.py
  __main__.py        # python -m webviz
  server.py
  scenarios.py
  fakes.py
  stream.py
  lessons/*.json
  static/{index.html, app.js, style.css}
tests/webviz/...
```

- Thêm optional dep vào `pyproject.toml`: `viz = ["fastapi", "uvicorn", "sse-starlette"]`.
- Chạy: `pip install -e ".[viz]"` rồi `python -m webviz` → mở `http://localhost:8000`.

## 10. Bài học ↔ minh họa (đã xác nhận đủ cả 7 phần)

| Phần | Bài học | Công tắc / yếu tố GUI |
|---|---|---|
| 1 LLM client | abstraction, retry, timeout, cost, logging | toggle retry+timeout · badge LLM · metrics cost |
| 2 Search client | abstraction, chuẩn hóa biên, grounding, logging | toggle search · badge Search · thẻ SourceDocument · fault vào search |
| 3 Supervisor | route theo state, guardrail, orchestrator không làm việc, control vs obs, tập trung | toggle max_iter · decision box · 2 làn |
| 4 Workers | single responsibility, qua state, cùng-LLM-khác-mũ, hợp đồng, refinement, token/agent | ô đọc/ghi · panel "chiếc mũ" · single↔multi |
| 5 LangGraph | đồ thị khai báo, conditional, loop-back, adapter, build/run, .stream() | animate edge đứt/liền |
| 6 Tracing | hạng nhất, fail-open, opt-in, span, lồng, 2 tầng | nút gây lỗi tracing · duration |
| 7 Benchmark | đo không cảm tính, đa chiều, cost thật, proxy trung thực, runner cắm được, báo cáo quyết định | so sánh cạnh nhau + bar · xuất report.md |
