import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from agent.guardrails import PatchProposal, evaluate_patch_proposal
from agent.state import AgentState
from agent.tools import discover_framework, read_source_file
from frameworks.factory import FactoryFramework


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_IGNORED_SOURCE_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "tests",
    "__tests__",
}
_SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
_MAX_SOURCE_FILES = 12
_MAX_SOURCE_CONTEXT_CHARS = 24000
_MAX_FAILURE_OUTPUT_CHARS = 10000


class PatchSuggestion(BaseModel):
    file_path: str
    old_content: str
    new_content: str
    rationale: str


class FailureAnalysis(BaseModel):
    summary: str
    proposal: PatchSuggestion | None = None


def _analyze_failures(context: str) -> FailureAnalysis:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from the environment or .env file.")

    model = ChatGroq(
        model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
        api_key=api_key,
        temperature=0,
        max_tokens=1000,
        timeout=30,
        max_retries=0,
    )
    structured_model = model.with_structured_output(FailureAnalysis)
    return structured_model.invoke([
        SystemMessage(content=(
            "Analyze the supplied test failures and source. Return a concise summary and "
            "at most one focused patch proposal. Do not propose test or policy changes. "
            "The old_content must be copied exactly from the supplied source. If a safe, "
            "well-supported patch cannot be proposed, set proposal to null."
        )),
        HumanMessage(content=context),
    ])


def _collect_source_context(project_dir: Path) -> list[dict[str, str]]:
    source_files = []
    total_chars = 0

    for current_dir, directory_names, file_names in os.walk(project_dir):
        directory_names[:] = sorted(
            name for name in directory_names
            if name.casefold() not in _IGNORED_SOURCE_DIRECTORIES
        )
        for file_name in sorted(file_names):
            source_path = Path(current_dir) / file_name
            if source_path.suffix.casefold() not in _SOURCE_EXTENSIONS:
                continue

            relative_path = source_path.relative_to(project_dir).as_posix()
            content = read_source_file.invoke({
                "project_path": str(project_dir),
                "file_path": relative_path,
            })
            if not isinstance(content, str) or content.startswith("Error:"):
                continue
            if total_chars + len(content) > _MAX_SOURCE_CONTEXT_CHARS:
                continue

            source_files.append({"file_path": relative_path, "content": content})
            total_chars += len(content)
            if len(source_files) >= _MAX_SOURCE_FILES:
                return source_files

    return source_files


def _run_tests(project_dir: Path) -> tuple[list[dict], list[dict]]:
    detected_projects = json.loads(discover_framework.invoke({
        "project_path": str(project_dir),
    }))
    if not detected_projects:
        return [], []

    framework_results = []
    failed_tests = []
    for detected in detected_projects:
        framework = detected["framework"]
        adapter = FactoryFramework.getAdapter(framework)
        test_paths = adapter.discover_tests(str(project_dir))
        results = []

        for test_path in test_paths:
            result = adapter.run_test(str(project_dir), test_path)
            exit_code = result.get("exit_code", result.get("exit", 1))
            test_result = {
                "test_path": test_path,
                "exit_code": exit_code,
            }
            results.append(test_result)

            if exit_code != 0:
                failed_tests.append({
                    "framework": framework,
                    "test_path": test_path,
                    "exit_code": exit_code,
                    "stdout": result.get("stdout", "")[-_MAX_FAILURE_OUTPUT_CHARS:],
                    "stderr": result.get("stderr", "")[-_MAX_FAILURE_OUTPUT_CHARS:],
                    "test_source": adapter.read_test_file(str(project_dir), test_path),
                })

        framework_results.append({
            "framework": framework,
            "tests_discovered": len(test_paths),
            "tests": results,
        })

    return framework_results, failed_tests


def _overall_decision(decisions: list[dict]) -> str:
    actions = {decision["decision"] for decision in decisions}
    if actions == {"REQUIRE_APPROVAL"}:
        return "REQUIRE_APPROVAL"
    if "REJECT" in actions:
        return "REJECT"
    if "SUGGEST_ONLY" in actions:
        return "SUGGEST_ONLY"
    return "REJECT"


def _run_tests_node(state: AgentState) -> AgentState:
    project_dir = Path(state["project_path"]).resolve(strict=True)
    if not project_dir.is_dir():
        raise ValueError("Project path must point to a directory.")

    framework_results, failed_tests = _run_tests(project_dir)
    update: AgentState = {
        "framework_results": framework_results,
        "failed_tests": failed_tests,
    }
    if not framework_results:
        update.update({
            "status": "no_framework",
            "message": "No supported test framework was detected in the selected project.",
        })
    elif not any(result["tests_discovered"] for result in framework_results):
        update.update({"status": "no_tests"})
    elif not failed_tests:
        update.update({
            "status": "tests_passed",
            "message": "All discovered tests passed. No LLM request or patch proposal was needed.",
        })
    return update


def _route_after_tests(state: AgentState) -> str:
    return "analyze_failures" if state["failed_tests"] else "finalize"


def _analyze_failures_node(state: AgentState) -> AgentState:
    project_dir = Path(state["project_path"]).resolve(strict=True)
    failure_context = json.dumps({
        "project_path": str(project_dir),
        "test_results": state["framework_results"],
        "failures": state["failed_tests"],
        "source_files": _collect_source_context(project_dir),
    }, indent=2)

    try:
        analysis = _analyze_failures(failure_context)
    except Exception as error:
        return {
            "status": "analysis_failed",
            "message": f"Tests failed, but LLM analysis could not complete: {error}",
        }

    return {
        "status": "no_proposal" if analysis.proposal is None else "proposal_pending_validation",
        "summary": analysis.summary,
        "proposal": analysis.proposal.model_dump() if analysis.proposal else None,
    }


def _route_after_analysis(state: AgentState) -> str:
    return "validate_proposal" if state.get("proposal") else "finalize"


def _validate_proposal_node(state: AgentState) -> AgentState:
    project_path = state["project_path"]
    proposal = PatchProposal(**state["proposal"])
    decisions = []
    for framework_result in state["framework_results"]:
        decision = evaluate_patch_proposal(
            project_path,
            proposal,
            framework_result["framework"],
        )
        decisions.append({
            "framework": framework_result["framework"],
            "decision": decision.action.value,
            "reason": decision.reason,
            "category": decision.category,
            "validation_passed": decision.validation_passed,
        })

    return {"status": "proposal_reviewed", "decisions": decisions}


def _finalize_node(state: AgentState) -> AgentState:
    result = {"status": state["status"]}
    if "framework_results" in state:
        result["frameworks"] = state["framework_results"]
    if "summary" in state:
        result["summary"] = state["summary"]
    if state.get("proposal"):
        result["proposal"] = state["proposal"]
    if "decisions" in state:
        result["decision"] = _overall_decision(state["decisions"])
        result["framework_decisions"] = state["decisions"]
        result["message"] = "No files were changed. Human approval is required for any proposal."
    elif "message" in state:
        result["message"] = state["message"]
    state["result"] = json.dumps(result, indent=2)
    return {"result": state["result"]}


def _build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("run_tests", _run_tests_node)
    graph.add_node("analyze_failures", _analyze_failures_node)
    graph.add_node("validate_proposal", _validate_proposal_node)
    graph.add_node("finalize", _finalize_node)

    graph.add_edge(START, "run_tests")
    graph.add_conditional_edges("run_tests", _route_after_tests, {
        "analyze_failures": "analyze_failures",
        "finalize": "finalize",
    })
    graph.add_conditional_edges("analyze_failures", _route_after_analysis, {
        "validate_proposal": "validate_proposal",
        "finalize": "finalize",
    })
    graph.add_edge("validate_proposal", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


_AGENT_GRAPH = _build_agent_graph()


def run_agent(project_path: str) -> str:
    """Run the QA workflow graph and return its JSON result."""
    final_state = _AGENT_GRAPH.invoke({"project_path": project_path})
    return final_state["result"]