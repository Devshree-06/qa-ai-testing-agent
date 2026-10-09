from langchain_core.tools import tool

import json

from pathlib import Path

from frameworks.factory import FactoryFramework

from agent.guardrails import PatchProposal, evaluate_patch_proposal

@tool
def discover_framework(project_path: str):

   """Detect supported test frameworks in the selected project directory."""
   project_dir = Path(project_path).resolve()
   if not project_dir.is_dir():
      return json.dumps([])

   projects = []
   python_markers = ("pytest.ini", "pyproject.toml", "setup.cfg")
   has_python_tests = any(project_dir.glob("tests/test_*.py"))
   if any((project_dir / marker).is_file() for marker in python_markers) or has_python_tests:
      projects.append({"project_path": str(project_dir), "framework": "pytest"})

   package_json_path = project_dir / "package.json"
   if package_json_path.is_file():
      try:
         package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
      except (OSError, UnicodeError, json.JSONDecodeError):
         package_json = {}

      if isinstance(package_json, dict):
         dependencies = package_json.get("dependencies", {})
         dev_dependencies = package_json.get("devDependencies", {})
         has_jest = (
            isinstance(dependencies, dict) and "jest" in dependencies
         ) or (
            isinstance(dev_dependencies, dict) and "jest" in dev_dependencies
         )
         if has_jest:
            projects.append({"project_path": str(project_dir), "framework": "jest"})

   return json.dumps(projects)


@tool
def run_test(framework :str,project_path:str,test_path: str) -> str:
    """Call this method to execute the tests"""

    adapter = FactoryFramework.getAdapter(framework)

    result = adapter.run_test(project_path,test_path)

    return json.dumps(result)

@tool
def discover_tests(framework :str,project_path:str) -> str:
   """Run this method to discover the tests present in the project"""

   adapter = FactoryFramework.getAdapter(framework)
   
   result = adapter.discover_tests(project_path)
   return json.dumps(result)


@tool
def read_test_file(framework :str,project_path:str,test_path:str) -> str:
   """Call this method to read the test file and analyze it and provide your output"""
   adapter = FactoryFramework.getAdapter(framework)
  
   result = adapter.read_test_file(project_path,test_path)
   return json.dumps(result)


@tool
def read_source_file(project_path: str, file_path: str) -> str:
   """Read an in-project source file so a proposal can match exact original text."""
   project_dir = Path(project_path).resolve()
   proposed_path = Path(file_path)
   if proposed_path.is_absolute() or ".." in proposed_path.parts:
      return "Error: source path must stay inside the project."

   try:
      source_file = (project_dir / proposed_path).resolve(strict=True)
      source_file.relative_to(project_dir)
   except (OSError, RuntimeError, ValueError):
      return "Error: source file does not exist inside the project."

   relative_parts = source_file.relative_to(project_dir).parts
   blocked_parts = {".git", ".venv", "venv", "node_modules", "tests", "__tests__"}
   name = source_file.name.casefold()
   if (
      not source_file.is_file()
      or source_file.suffix.casefold() not in {".py", ".js", ".jsx", ".ts", ".tsx"}
      or any(part.casefold() in blocked_parts for part in relative_parts)
      or name.startswith(".env")
      or name.startswith("test_")
      or name.endswith("_test.py")
      or ".test." in name
      or ".spec." in name
      or name == "conftest.py"
   ):
      return "Error: only non-test source code files can be read."

   try:
      content = source_file.read_text(encoding="utf-8")
   except (OSError, UnicodeError):
      return "Error: source file could not be read as UTF-8."

   if len(content) > 20000:
      return "Error: source file exceeds the 20,000-character read limit."
   return content


@tool
def propose_patch(
    project_path: str,
    framework: str,
    file_path: str,
    old_content: str,
    new_content: str,
    rationale: str,
) -> str:
    """
    Submit a proposed code change for deterministic policy review.
    This tool never modifies files. Valid proposals require human approval.
    """
    proposal = PatchProposal(
        file_path=file_path,
        old_content=old_content,
        new_content=new_content,
        rationale=rationale,
    )
    decision = evaluate_patch_proposal(project_path, proposal, framework)
    return json.dumps({
        "proposal": proposal.to_dict(),
        "decision": decision.action.value,
        "reason": decision.reason,
        "category": decision.category,
        "validation_passed": decision.validation_passed,
    })

