import json
from pathlib import Path

from agent.guardrails import (
    DecisionAction,
    PatchProposal,
    evaluate_patch_proposal,
)


def _proposal(file_path: str, old_content: str, new_content: str) -> PatchProposal:
    return PatchProposal(
        file_path=file_path,
        old_content=old_content,
        new_content=new_content,
        rationale="Address the observed test failure.",
    )


class PassingAdapter:
    def __init__(self, result_code=0):
        self.result_code = result_code
        self.project_path = None

    def discover_tests(self, project_path):
        self.project_path = project_path
        return ["tests/test_module.py"]

    def run_test(self, project_path, test_path):
        assert project_path == self.project_path
        assert (Path(project_path) / "src/module.py").read_text(encoding="utf-8") == "value = 2\n"
        return {"exit_code": self.result_code, "stdout": "", "stderr": ""}


def _write_project(tmp_path, *, normal_paths=None, business_paths=None):
    source = tmp_path / "src" / "module.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    test_file = tmp_path / "tests" / "test_module.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_placeholder(): pass\n", encoding="utf-8")
    (tmp_path / "qa-agent-policy.json").write_text(
        json.dumps({
            "normal_bug_paths": normal_paths or [],
            "business_requirement_paths": business_paths or [],
        }),
        encoding="utf-8",
    )
    return source


def test_valid_normal_proposal_is_tested_in_copy_and_requires_approval(tmp_path, monkeypatch):
    import agent.guardrails as guardrails

    target = _write_project(tmp_path, normal_paths=["src/**"])
    adapter = PassingAdapter()
    monkeypatch.setattr(
        guardrails.FactoryFramework,
        "getAdapter",
        lambda framework: adapter,
    )

    decision = evaluate_patch_proposal(
        str(tmp_path),
        _proposal("src/module.py", "value = 1", "value = 2"),
        "pytest",
    )

    assert decision.action is DecisionAction.REQUIRE_APPROVAL
    assert decision.category == "normal_bug"
    assert decision.validation_passed is True
    assert target.read_text(encoding="utf-8") == "value = 1\n"
    assert Path(adapter.project_path) != tmp_path


def test_business_path_requires_approval_even_when_tests_pass(tmp_path, monkeypatch):
    import agent.guardrails as guardrails

    _write_project(tmp_path, business_paths=["src/**"])
    monkeypatch.setattr(guardrails.FactoryFramework, "getAdapter", lambda _: PassingAdapter())

    decision = evaluate_patch_proposal(
        str(tmp_path),
        _proposal("src/module.py", "value = 1", "value = 2"),
        "pytest",
    )

    assert decision.action is DecisionAction.REQUIRE_APPROVAL
    assert decision.category == "business_requirement"
    assert decision.validation_passed is True


def test_unclassified_path_is_suggestion_only(tmp_path):
    _write_project(tmp_path)

    decision = evaluate_patch_proposal(
        str(tmp_path),
        _proposal("src/module.py", "value = 1", "value = 2"),
        "pytest",
    )

    assert decision.action is DecisionAction.SUGGEST_ONLY
    assert decision.category == "unclassified"


def test_rejects_test_file_modification(tmp_path):
    target = tmp_path / "tests" / "test_module.py"
    target.parent.mkdir()
    target.write_text("assert True\n", encoding="utf-8")

    decision = evaluate_patch_proposal(
        str(tmp_path),
        _proposal("tests/test_module.py", "assert True", "assert False"),
        "pytest",
    )

    assert decision.action is DecisionAction.REJECT


def test_rejects_path_outside_project(tmp_path):
    decision = evaluate_patch_proposal(
        str(tmp_path),
        _proposal("../outside.py", "before", "after"),
    )

    assert decision.action is DecisionAction.REJECT


def test_rejects_protected_file(tmp_path):
    target = tmp_path / ".env"
    target.write_text("TOKEN=value", encoding="utf-8")

    decision = evaluate_patch_proposal(
        str(tmp_path),
        _proposal(".env", "TOKEN=value", "TOKEN=other"),
    )

    assert decision.action is DecisionAction.REJECT


def test_rejects_stale_or_ambiguous_original_text(tmp_path):
    target = tmp_path / "module.py"
    target.write_text("value = 1\nvalue = 1\n", encoding="utf-8")

    decision = evaluate_patch_proposal(
        str(tmp_path),
        _proposal("module.py", "value = 1", "value = 2"),
    )

    assert decision.action is DecisionAction.REJECT


def test_rejects_candidate_when_tests_fail(tmp_path, monkeypatch):
    import agent.guardrails as guardrails

    _write_project(tmp_path, normal_paths=["src/**"])
    monkeypatch.setattr(
        guardrails.FactoryFramework,
        "getAdapter",
        lambda _: PassingAdapter(result_code=1),
    )

    decision = evaluate_patch_proposal(
        str(tmp_path),
        _proposal("src/module.py", "value = 1", "value = 2"),
        "pytest",
    )

    assert decision.action is DecisionAction.REJECT
    assert decision.validation_passed is False


def test_rejects_invalid_trusted_policy(tmp_path):
    source = tmp_path / "src" / "module.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "qa-agent-policy.json").write_text("not json", encoding="utf-8")

    decision = evaluate_patch_proposal(
        str(tmp_path),
        _proposal("src/module.py", "value = 1", "value = 2"),
        "pytest",
    )

    assert decision.action is DecisionAction.REJECT

