from langchain_core.tools import tool

import json

from pathlib import Path

from frameworks.factory import FactoryFramework

import json

@tool
def discover_framework(project_path: str):

   """Detect which test framework is used by the project"""

   workspace_dir = Path(project_path).resolve()

   projects = []

   print("Workspace directory fetched : " + str(workspace_dir))

   for project_dir in workspace_dir.iterdir():
      if not project_dir.iterdir():
         continue

      framework = None

      print("Project directory fetched : " + str(project_dir))

      package_json_path = project_dir/"package.json"

      if (package_json_path).exists():

         package_json = json.loads(package_json_path.read_text(encoding="utf-8"))

         dependencies = package_json.get("dependences",{})

         dev_dependencies = package_json.get("devDependencies",{})

         if "jest" in dependencies or "jest" in dev_dependencies:
            framework =  "jest"
 
      if (project_dir/"pytest.ini").exists():

               print("python package found")
               framework =  "pytest"

      if framework:
         projects.append({
         "project_path" : str(project_dir),
         "framework"  : framework
      })

   print("Th projects returned : " , projects)
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


def safe_apply_patch(file_path:str) -> bool:

   print("Calling the safe apply patch method")

   path = Path(file_path)

   if "tests" in path.parts:
      return True

   if path.name.startswith("test_"):
      return True

   if path.name.endswith("_test.py"):
      return True


   return False


@tool
def apply_patch(project_path: str,file_path:str,old_content:str,new_content: str):
    """
    Replace old_content with new_content in a file.

    IMPORTANT:
    - old_content must be the exact text currently present in the file.
    - new_content must be the replacement text.
    - Do not use any other parameter names.
    - The tool modifies only the specified file.
    """

    project_dir = Path(project_path).resolve()

    target_file = (project_dir / file_path).resolve()

    if not safe_apply_patch(file_path):
       return "`BLOCKED: Automatic patching not allowed for this file."


    if not target_file.is_relative_to(project_dir):
      return "ERROR: File is outside project directory"

    protected_files = [
      ".env",
      ".gitignore"

   ]

    if not target_file.exists():     
      return f"ERROR: File '{file_path}' does not exist "

    if target_file.name in protected_files:
         return "ERROR: This file is protected and cannot be modified."

    content = target_file.read_text(
      encoding="utf-8"
   )

    if old_content not in content:
      return (
         "ERROR: The old content was not found in the file. "
         "No changes were made"
      )

    updated_content = content.replace(
      old_content,
      new_content,
      1
   )

    target_file.write_text(
      updated_content,
      encoding="utf-8"
   )

    return (
     f"SUCCESS : Updated '{file_path}'. "
     "The requested patch was applied." 
   )

