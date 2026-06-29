from webviz.contracts import StreamEvent, EdgeTaken, Lesson, LessonOption, GlossaryItem


def test_stream_event_round_trips():
    ev = StreamEvent(
        kind="node",
        step=1,
        active_node="researcher",
        edge_taken=EdgeTaken(source="supervisor", target="researcher", style="dashed"),
        state_snapshot={"research_notes": "x"},
        metrics={"latency_seconds": 0.0, "estimated_cost_usd": 0.0, "citation_coverage": 0.0},
        lane={"control": {"route_history": ["researcher"], "iteration": 1}, "observability": {"trace": []}},
        note="Researcher chạy",
    )
    dumped = ev.model_dump()
    assert dumped["kind"] == "node"
    assert dumped["edge_taken"]["style"] == "dashed"
    assert dumped["lane"]["control"]["iteration"] == 1


def test_stream_event_minimal_defaults():
    ev = StreamEvent(kind="error", step=0, note="boom")
    assert ev.active_node is None
    assert ev.edge_taken is None
    assert ev.state_snapshot == {} and ev.metrics == {}
    assert ev.lane == {"control": {}, "observability": {}}


def test_lesson_model():
    lesson = Lesson(
        id="retry-timeout",
        title="Retry & timeout",
        option_a=LessonOption(label="Có retry", code="x=1", source_ref="src/a.py:1-2", narration="..."),
        option_b=LessonOption(label="Không retry", code="y=2", source_ref=None, narration="..."),
        glossary=[GlossaryItem(term="retry", vi="thử lại tự động khi gặp lỗi tạm thời")],
    )
    assert lesson.option_b.source_ref is None
    assert lesson.glossary[0].term == "retry"
