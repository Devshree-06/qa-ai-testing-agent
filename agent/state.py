
from typing import TypedDict


class AgentState(TypedDict, total=False):
    project_path: str
    framework_results: list[dict]
    failed_tests: list[dict]
    status: str
    summary: str
    proposal: dict[str, str] | None
    decisions: list[dict]
    message: str
    result: str