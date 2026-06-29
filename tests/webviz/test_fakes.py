import pytest

from webviz.fakes import FakeLLMClient, FakeSearchClient
from multi_agent_research_lab.core.schemas import SourceDocument

RESEARCHER = "You are a research specialist."
ANALYST = "You are a critical analyst."
WRITER = "You are a technical writer targeting x."
BASELINE = "You are a research assistant."


def test_llm_is_deterministic_and_role_aware():
    a = FakeLLMClient().complete(RESEARCHER, "q")
    b = FakeLLMClient().complete(RESEARCHER, "q")
    assert a.content == b.content
    assert a.input_tokens and a.output_tokens and a.cost_usd is not None
    # writer output must contain a [1] citation so coverage > 0
    w = FakeLLMClient().complete(WRITER, "q")
    assert "[1]" in w.content
    # distinct roles produce distinct content
    assert FakeLLMClient().complete(ANALYST, "q").content != a.content


def test_llm_fail_first_recovers_with_retry():
    c = FakeLLMClient(fault="fail_first", retry=True)
    assert c.complete(RESEARCHER, "q").content  # 1st attempt fails internally, 2nd succeeds


def test_llm_fail_first_dies_without_retry():
    c = FakeLLMClient(fault="fail_first", retry=False)
    with pytest.raises(RuntimeError):
        c.complete(RESEARCHER, "q")


def test_llm_withhold_returns_none_content():
    c = FakeLLMClient(withhold_roles={"researcher"})
    assert c.complete(RESEARCHER, "q").content is None
    assert c.complete(ANALYST, "q").content is not None


def test_search_normal_empty_and_fault():
    docs = FakeSearchClient().search("q", max_results=3)
    assert docs and all(isinstance(d, SourceDocument) for d in docs)
    assert FakeSearchClient(mode="empty").search("q") == []
    with pytest.raises(RuntimeError):
        FakeSearchClient(fault=True).search("q")
