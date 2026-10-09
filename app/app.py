import argparse
import difflib
import json
import os
from pathlib import Path

from dotenv import load_dotenv


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI QA agent on one project.")
    parser.add_argument(
        "--project-path",
        default=str(REPOSITORY_ROOT / "workspace" / "demo-project"),
        help="Project directory to inspect (defaults to the Python demo project).",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.is_dir():
        parser.error(f"Project directory does not exist: {project_path}")

    load_dotenv(REPOSITORY_ROOT / ".env")

    from agent.agent import run_agent
    from agent.guardrails import PatchProposal, apply_approved_patch

    result = json.loads(run_agent(str(project_path)))
    if result.get("status") == "analysis_failed" and not os.getenv("GROQ_API_KEY"):
        result["message"] += " Add GROQ_API_KEY to the repository .env file to enable failure analysis."
    framework_decisions = result.get("framework_decisions", [])
    can_review = (
        result.get("status") == "proposal_reviewed"
        and result.get("decision") == "REQUIRE_APPROVAL"
        and framework_decisions
        and all(item.get("validation_passed") is True for item in framework_decisions)
    )

    if can_review:
        proposal_data = result["proposal"]
        proposal = PatchProposal(**proposal_data)
        print(result.get("summary", "Patch proposal"))
        print("".join(difflib.unified_diff(
            proposal.old_content.splitlines(keepends=True),
            proposal.new_content.splitlines(keepends=True),
            fromfile=f"a/{proposal.file_path}",
            tofile=f"b/{proposal.file_path}",
        )), end="")
        try:
            approved = input("Apply this patch to the project? [y/N]: ").strip().casefold() in {"y", "yes"}
        except EOFError:
            approved = False

        if approved:
            applied, message = apply_approved_patch(str(project_path), proposal)
            result["approval"] = "approved"
            result["application"] = {"applied": applied, "message": message}
        else:
            result["approval"] = "rejected"
            result["application"] = {
                "applied": False,
                "message": "Patch was not applied.",
            }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()