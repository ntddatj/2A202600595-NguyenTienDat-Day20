# webviz — Lab 20 Multi-Agent Teaching GUI

Trực quan hóa workflow multi-agent thật trong `src/multi_agent_research_lab` (chỉ đọc, không sửa).

## Cài đặt & chạy
```bash
pip install -e ".[viz,llm]"
python -m webviz                 # mặc định http://127.0.0.1:8000
python -m webviz --host 0.0.0.0 --port 8080
```
- **Mock mode** là mặc định: chạy offline, deterministic, không cần API key.
- **Live mode**: tích "Live" (cần `OPENAI_API_KEY`/`TAVILY_API_KEY`). Thiếu key → hiện cảnh báo, không sập.

## Học gì
- Gạt 4 công tắc (multi/retry/max_iter/search) — panel bài học tự mở thuyết minh + dòng "trước → sau".
- Bấm node/edge/lane/badge để xem code thật tương ứng.
- Nút "gây lỗi tracing" minh họa fail-open. Nút "Xuất benchmark_report.md" gọi `render_markdown_report` thật.

## Test
```bash
python -m pytest tests/webviz -q
```
