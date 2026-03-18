from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SMOKE_PATH = Path(__file__).parent.parent / "eval_retrieval_smoke.py"


def _load_smoke():
    spec = importlib.util.spec_from_file_location("eval_retrieval_smoke", _SMOKE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestEvalRetrievalSmoke:
    def test_build_retrieval_smoke_cases_crosses_agent_boundaries(self):
        mod = _load_smoke()

        cases = mod.build_retrieval_smoke_cases(agent_count=5, question_offset=2)

        assert len(cases) == 5
        assert [case.target_agent for case in cases] == [0, 1, 2, 3, 4]
        assert [case.subject_agent for case in cases] == [2, 3, 4, 0, 1]
        assert all(case.target_agent != case.subject_agent for case in cases)
        assert cases[0].expected_codename == "ORBIT-2"
        assert cases[0].question == "What is the codename for retrieval smoke record 2?"

    def test_zero_offset_normalizes_to_cross_agent_question(self):
        mod = _load_smoke()

        cases = mod.build_retrieval_smoke_cases(agent_count=4, question_offset=0)

        assert [case.subject_agent for case in cases] == [1, 2, 3, 0]
        assert all(case.target_agent != case.subject_agent for case in cases)
        assert all(case.question.startswith("What is ") for case in cases)
        assert all(case.question.endswith("?") for case in cases)

    def test_answer_contains_expected_is_case_insensitive(self):
        mod = _load_smoke()

        assert mod.answer_contains_expected("The codename is orbit-9.", "ORBIT-9")
        assert not mod.answer_contains_expected("No relevant codename found.", "ORBIT-9")
