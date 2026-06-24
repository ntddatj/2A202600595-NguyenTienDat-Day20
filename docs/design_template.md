# Design Template

## Problem

Xây dựng hệ thống research assistant tự động: nhận một câu hỏi kỹ thuật, tìm kiếm thông tin từ web, phân tích và tổng hợp thành câu trả lời có dẫn nguồn. Ví dụ query: *"Research GraphRAG state-of-the-art and write a 500-word summary"*.

## Why multi-agent?

Single-agent có hai vấn đề khi xử lý research tasks phức tạp:

1. **Context overload**: một agent phải đồng thời tìm nguồn, phán đoán độ tin cậy, so sánh viewpoints và viết — quá nhiều nhiệm vụ dẫn đến output thiếu chiều sâu.
2. **Không có kiểm tra chéo**: output không qua bước phân tích độc lập nên dễ bỏ sót weak evidence hoặc hallucinate.

Multi-agent tách rõ trách nhiệm: Researcher chỉ tìm, Analyst chỉ phán đoán, Writer chỉ tổng hợp — mỗi bước dùng prompt chuyên biệt nên chất lượng từng khâu cao hơn.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Routing: quyết định agent nào chạy tiếp, khi nào dừng | `ResearchState` hiện tại | Cập nhật `route_history` | Max iterations — force `done` |
| Researcher | Tìm kiếm web + tóm tắt thành research notes có đánh số | `request.query`, `request.max_sources` | `sources: list[SourceDocument]`, `research_notes: str` | Tavily rate limit → 0 kết quả |
| Analyst | Phân tích notes: extract claims, so sánh viewpoints, flag weak evidence | `research_notes` | `analysis_notes: str` | Prompt quá dài → truncation |
| Writer | Tổng hợp final answer với citation [N] từ sources | `research_notes`, `analysis_notes`, `sources` | `final_answer: str` | Hallucinate citation index không có thật |

## Shared state

`ResearchState` (Pydantic model) — single source of truth qua toàn bộ workflow:

| Field | Type | Lý do cần |
|---|---|---|
| `request` | `ResearchQuery` | Giữ query gốc, max_sources, audience để agents tham chiếu nhất quán |
| `iteration` | `int` | Supervisor dùng để enforce `max_iterations` guardrail |
| `route_history` | `list[str]` | LangGraph conditional edge đọc entry cuối để route; cũng là audit trail |
| `sources` | `list[SourceDocument]` | Researcher ghi, Writer đọc để tạo citation [N] |
| `research_notes` | `str \| None` | Signal cho Supervisor: nếu None → gọi Researcher |
| `analysis_notes` | `str \| None` | Signal cho Supervisor: nếu None → gọi Analyst |
| `final_answer` | `str \| None` | Signal cho Supervisor: nếu None → gọi Writer; nếu có → done |
| `agent_results` | `list[AgentResult]` | Benchmark dùng để tính token cost và tạo summary |
| `trace` | `list[dict]` | Lightweight trace event log (bổ sung cho LangSmith) |
| `errors` | `list[str]` | Accumulate lỗi không fatal để debug sau |

## Routing policy

```
START
  │
  ▼
Supervisor ──► research_notes is None? ──► Researcher ─┐
  │                                                      │
  │◄─────────────────────────────────────────────────────┘
  │
  ├──► analysis_notes is None? ──► Analyst ─┐
  │                                          │
  │◄─────────────────────────────────────────┘
  │
  ├──► final_answer is None? ──► Writer ─┐
  │                                       │
  │◄──────────────────────────────────────┘
  │
  ├──► iteration >= max_iterations? ──► DONE (force stop)
  │
  └──► all fields populated? ──► DONE
```

Mỗi worker chạy xong đều quay lại Supervisor trước khi chạy worker tiếp theo.

## Guardrails

- **Max iterations**: `MAX_ITERATIONS=6` (env), Supervisor force `done` khi vượt ngưỡng
- **Timeout**: `TIMEOUT_SECONDS=60` (env), truyền vào `openai.Client` qua `LLMClient.complete()`
- **Retry**: `tenacity` retry tối đa 3 lần với exponential backoff (2s → 10s) trong `LLMClient`
- **Fallback**: nếu Tavily trả về 0 kết quả, `research_notes` vẫn được tạo từ prompt không có sources
- **Validation**: Pydantic v2 validate toàn bộ `ResearchState` và input/output schemas ở mọi boundary

## Benchmark plan

**Queries thử nghiệm:**
1. "What is LangGraph and how does it compare to simple LLM chains for building AI agents?"
2. "Research GraphRAG state-of-the-art and write a 500-word summary"

**Metrics đo:**

| Metric | Cách đo | Expected: single | Expected: multi |
|---|---|---|---|
| Latency (s) | `perf_counter` wall-clock | ~10s | ~30s (+3× do 3 LLM calls) |
| Cost (USD) | token × pricing | ~$0.0004 | ~$0.0012 (+3×) |
| Citation coverage | `[N]` hits / len(sources) | 0% (không có sources) | 80-100% |
| Quality (0-10) | Peer review rubric | 6-7 (generic) | 8-9 (có structure + sources) |
| Error rate | fails / total runs | ~0% | ~0% (retry bắt được) |

**Kết luận mong đợi:** Multi-agent đắt và chậm hơn ~3× nhưng output có dẫn nguồn, structured hơn — xứng đáng khi query phức tạp cần độ tin cậy cao.
