from dataclasses import asdict, dataclass
from enum import Enum
import fnmatch
import json
from pathlib import Path
import shutil
import tempfile

from frameworks.factory import FactoryFramework


class DecisionAction(str, Enum):
    REJECT = "REJECT"
    SUGGEST_ONLY = "SUGGEST_ONLY"
    APPLY_IN_SANDBOX = "APPLY_IN_SANDBOX"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass(frozen=True)
class PatchProposal:
    file_path: str
    old_content: str
    new_content: str
    rationale: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PolicyDecision:
    action: DecisionAction
    reason: str
    category: str = "unclassified"
    validation_passed: bool | None = None


_PROTECTED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
}

_PROTECTED_FILENAMES = {
    ".gitignore",
    ".env",
    "qa-agent-policy.json",
}

_POLICY_FILENAME = "qa-agent-policy.json"
_IGNORED_COPY_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
}


def _is_test_file(path: Path) -> bool:
    parts = {part.casefold() for part in path.parts}
    name = path.name.casefold()
    return (
        bool(parts & {"test", "tests", "__tests__"})
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
        or name == "conftest.py"
    )


def _load_path_categories(project_dir: Path) -> tuple[set[str], set[str]] | None:
    policy_path = project_dir / _POLICY_FILENAME
    if not policy_path.exists():
        return set(), set()

    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    if not isinstance(policy, dict):
        return None

    normal_paths = policy.get("normal_bug_paths", [])
    business_paths = policy.get("business_requirement_paths", [])
    if (
        not isinstance(normal_paths, list)
        or not isinstance(business_paths, list)
        or not all(isinstance(pattern, str) and pattern for pattern in normal_paths + business_paths)
    ):
        return None

    return set(normal_paths), set(business_paths)


def _classify_path(relative_path: Path, categories: tuple[set[str], set[str]]) -> str:
    relative_name = relative_path.as_posix()
    normal_paths, business_paths = categories
    is_normal = any(fnmatch.fnmatchcase(relative_name, pattern) for pattern in normal_paths)
    is_business = any(fnmatch.fnmatchcase(relative_name, pattern) for pattern in business_paths)

    if is_normal and is_business:
        return "conflict"
    if is_business:
        return "business_requirement"
    if is_normal:
        return "normal_bug"
    return "unclassified"


def _validate_in_temporary_copy(
    project_dir: Path,
    relative_target: Path,
    proposal: PatchProposal,
    framework: str,
) -> tuple[bool, str]:
    try:
        adapter = FactoryFramework.getAdapter(framework)
        with tempfile.TemporaryDirectory(prefix="qa-agent-validation-") as temporary_dir:
            temporary_project = Path(temporary_dir) / "project"

            def names_intersection(names: list[str], excluded: set[str]) -> set[str]:
                return {name for name in names if name.casefold() in excluded}

            def ignore_copy_entries(directory: str, names: list[str]) -> set[str]:
                return names_intersection(names, _IGNORED_COPY_DIRECTORIES)

            shutil.copytree(project_dir, temporary_project, ignore=ignore_copy_entries)

            temporary_target = temporary_project / relative_target
            current_content = temporary_target.read_text(encoding="utf-8")

            if current_content.count(proposal.old_content) != 1:
                return False, "Target changed while the proposal was being validated."

            temporary_target.write_text(
                current_content.replace(proposal.old_content, proposal.new_content, 1),
                encoding="utf-8",
            )

            test_paths = adapter.discover_tests(str(temporary_project))
            if not test_paths:
                return False, "No tests were discovered in the temporary project copy."

            failures = []
            for test_path in test_paths:
                result = adapter.run_test(str(temporary_project), test_path)
                exit_code = result.get("exit_code", result.get("exit", 1))
                if exit_code != 0:
                    failures.append(test_path)

            if failures:
                return False, f"Tests failed in the temporary copy: {', '.join(failures)}"

            return True, f"All {len(test_paths)} discovered test(s) passed in the temporary copy."
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        return False, f"Temporary validation could not be completed: {error}"


def evaluate_patch_proposal(
    project_path: str,
    proposal: PatchProposal,
    framework: str | None = None,
) -> PolicyDecision:
    """Validate scope and tests without modifying the original project."""
    try:
        project_dir = Path(project_path).resolve(strict=True)
    except (OSError, RuntimeError):
        return PolicyDecision(DecisionAction.REJECT, "Project directory is unavailable.")

    if not project_dir.is_dir():
        return PolicyDecision(DecisionAction.REJECT, "Project path is not a directory.")

    proposed_path = Path(proposal.file_path)
    if proposed_path.is_absolute() or ".." in proposed_path.parts:
        return PolicyDecision(DecisionAction.REJECT, "Proposal path must stay within the project.")

    try:
        target_file = (project_dir / proposed_path).resolve(strict=True)
        relative_target = target_file.relative_to(project_dir)
    except (OSError, RuntimeError, ValueError):
        return PolicyDecision(DecisionAction.REJECT, "Target file is missing or outside the project.")

    lowered_parts = [part.casefold() for part in relative_target.parts]
    if (
        any(part in _PROTECTED_DIRECTORIES for part in lowered_parts)
        or target_file.name.casefold() in _PROTECTED_FILENAMES
        or target_file.name.casefold().startswith(".env.")
        or _is_test_file(relative_target)
    ):
        return PolicyDecision(
            DecisionAction.REJECT,
            "Tests, policy, and protected files cannot be changed by an automatic proposal.",
        )

    if not target_file.is_file():
        return PolicyDecision(DecisionAction.REJECT, "Target must be an existing file.")

    if not proposal.old_content or proposal.old_content == proposal.new_content:
        return PolicyDecision(DecisionAction.REJECT, "Proposal does not contain a meaningful replacement.")

    if not proposal.rationale.strip():
        return PolicyDecision(DecisionAction.REJECT, "Proposal rationale is required.")

    try:
        current_content = target_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return PolicyDecision(DecisionAction.REJECT, "Target file cannot be safely read as UTF-8.")

    occurrences = current_content.count(proposal.old_content)
    if occurrences != 1:
        return PolicyDecision(
            DecisionAction.REJECT,
            "Original text must match exactly once in the current file.",
        )

    categories = _load_path_categories(project_dir)
    if categories is None:
        return PolicyDecision(DecisionAction.REJECT, "Trusted project policy is invalid or unreadable.")

    category = _classify_path(relative_target, categories)
    if category == "conflict":
        return PolicyDecision(
            DecisionAction.REJECT,
            "Path is classified as both normal and business-sensitive.",
        )
    if category == "unclassified":
        return PolicyDecision(
            DecisionAction.SUGGEST_ONLY,
            "No trusted policy classifies this path; the proposal is not eligible for automatic validation or application.",
            category,
        )

    if framework is None:
        return PolicyDecision(
            DecisionAction.REQUIRE_APPROVAL,
            "A framework is required to validate the proposed change.",
            category,
        )

    validation_passed, validation_reason = _validate_in_temporary_copy(
        project_dir,
        relative_target,
        proposal,
        framework,
    )
    if not validation_passed:
        return PolicyDecision(
            DecisionAction.REJECT,
            validation_reason,
            category,
            False,
        )

    if category == "business_requirement":
        reason = f"{validation_reason} Business-sensitive changes always require owner approval."
    else:
        reason = f"{validation_reason} The proposal passed checks but still requires human approval."

    return PolicyDecision(
        DecisionAction.REQUIRE_APPROVAL,
        reason,
        category,
        True,
    )


def apply_approved_patch(project_path: str, proposal: PatchProposal) -> tuple[bool, str]:
    """Apply a previously validated proposal after explicit human approval."""
    decision = evaluate_patch_proposal(project_path, proposal)
    if decision.action is not DecisionAction.REQUIRE_APPROVAL:
        return False, decision.reason

    try:
        project_dir = Path(project_path).resolve(strict=True)
        target_file = (project_dir / proposal.file_path).resolve(strict=True)
        target_file.relative_to(project_dir)
        current_content = target_file.read_text(encoding="utf-8")
        if current_content.count(proposal.old_content) != 1:
            return False, "Target changed after validation; the approved patch was not applied."

        target_file.write_text(
            current_content.replace(proposal.old_content, proposal.new_content, 1),
            encoding="utf-8",
        )
    except (OSError, UnicodeError, RuntimeError, ValueError) as error:
        return False, f"Approved patch could not be applied: {error}"

    return True, "Approved patch applied successfully."