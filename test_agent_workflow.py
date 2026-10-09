import json
from pathlib import Path
import sys

import pytest

from app import app as app_module
from agent import agent as agent_module
from agent.agent import FailureAnalysis, PatchSuggestion, run_agent


def test_failure_uses_one_analysis_call_and_returns_approval_without_applying(tmp_path, monkeypatch):
    (tmp_path / "pytest.ini").write_text("[pytest]\npythonpath = .\n", encoding="utf-8")
    (tmp_path / "qa-agent-policy.json").write_text(
        json.dumps({"normal_bug_paths": ["src/**"], "business_requirement_paths": []}),
        encoding="utf-8",
    )
    source = tmp_path / "src" / "math_utils.py"
    source.parent.mkdir()
    source.write_text("def increment(value):\n    return value\n", encoding="utf-8")
    (source.parent / "__init__.py").write_text("", encoding="utf-8")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_math_utils.py").write_text(
        "from src.math_utils import increment\n\n"
        "def test_increment():\n    assert increment(1) == 2\n",
        encoding="utf-8",
    )

    analysis_calls = []

    def analyze_once(context):
        analysis_calls.append(context)
        return FailureAnalysis(
            summary="The increment function returns its input unchanged.",
            proposal=PatchSuggestion(
                file_path="src/math_utils.py",
                old_content="return value",
                new_content="return value + 1",
                rationale="Return the next integer as required by the failing test.",
            ),
        )

    monkeypatch.setattr(agent_module, "_analyze_failures", analyze_once)

    result = json.loads(run_agent(str(tmp_path)))

    assert len(analysis_calls) == 1
    assert result["status"] == "proposal_reviewed"
    assert result["decision"] == "REQUIRE_APPROVAL"
    assert result["framework_decisions"][0]["validation_passed"] is True
    assert source.read_text(encoding="utf-8") == "def increment(value):\n    return value\n"


def test_passing_tests_skip_llm_analysis(monkeypatch, tmp_path):
    monkeypatch.setattr(
        agent_module,
        "_run_tests",
        lambda _: ([{"framework": "pytest", "tests_discovered": 1, "tests": []}], []),
    )
    monkeypatch.setattr(
        agent_module,
        "_analyze_failures",
        lambda _: pytest.fail("LLM analysis should not run when tests pass."),
    )

    result = json.loads(run_agent(str(tmp_path)))

    assert result["status"] == "tests_passed"
    assert result["frameworks"][0]["tests_discovered"] == 1


def test_no_framework_routes_directly_to_final_result(monkeypatch, tmp_path):
    monkeypatch.setattr(agent_module, "_run_tests", lambda _: ([], []))
    monkeypatch.setattr(
        agent_module,
        "_analyze_failures",
        lambda _: pytest.fail("LLM analysis should not run without a detected framework."),
    )

    result = json.loads(run_agent(str(tmp_path)))

    assert result["status"] == "no_framework"
    assert "No supported test framework" in result["message"]


@pytest.mark.parametrize(
    ("response", "expected_content", "expected_approval"),
    [
        ("yes", "value = 2\n", "approved"),
        ("no", "value = 1\n", "rejected"),
    ],
)
def test_cli_shows_diff_and_applies_only_after_approval(
    tmp_path,
    monkeypatch,
    capsys,
    response,
    expected_content,
    expected_approval,
):
    source = tmp_path / "src" / "module.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "qa-agent-policy.json").write_text(
        json.dumps({"normal_bug_paths": ["src/**"], "business_requirement_paths": []}),
        encoding="utf-8",
    )
    result = {
        "status": "proposal_reviewed",
        "summary": "Update the value.",
        "proposal": {
            "file_path": "src/module.py",
            "old_content": "value = 1\n",
            "new_content": "value = 2\n",
            "rationale": "The test expects the updated value.",
        },
        "decision": "REQUIRE_APPROVAL",
        "framework_decisions": [{"validation_passed": True}],
    }
    monkeypatch.setattr(agent_module, "run_agent", lambda _: json.dumps(result))
    monkeypatch.setattr(app_module, "load_dotenv", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["qa-agent", "--project-path", str(tmp_path)])
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    def answer_prompt(prompt):
        print(prompt, end="")
        return response

    monkeypatch.setattr("builtins.input", answer_prompt)

    app_module.main()

    output = capsys.readouterr().out
    assert "--- a/src/module.py" in output
    assert "+++ b/src/module.py" in output
    assert "-value = 1" in output
    assert "+value = 2" in output
    assert f'"approval": "{expected_approval}"' in output
    assert source.read_text(encoding="utf-8") == expected_content
