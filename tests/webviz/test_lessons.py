from pathlib import Path

from webviz.contracts import Lesson
from webviz.lessons_loader import load_lessons, LESSON_IDS


def test_all_expected_lessons_present():
    lessons = load_lessons()
    assert set(lessons) == set(LESSON_IDS)


def test_each_lesson_validates_and_source_refs_exist():
    for lid, lesson in load_lessons().items():
        assert isinstance(lesson, Lesson)
        ref = lesson.option_a.source_ref
        assert ref, f"{lid} option_a must cite a real src/ excerpt"
        path, _, lines = ref.partition(":")
        assert Path(path).exists(), f"{lid}: {path} does not exist"
        assert path.startswith("src/")
        assert lesson.glossary, f"{lid} needs at least one glossary entry"
