from langchain_core.tools import tool

import json

from pathlib import Path

from frameworks.factory import FactoryFramework

@tool
def discover_framework(project_path: str):

   """Detect which test framework is used by the project"""

   project_dir = Path(project_path).resolve()

   if (project_dir/"package.json").exists():

      package_json = (project_dir/"package.json").read_text(
         encoding="utf-8"
      )

      if "jest" in package_json:
         print("jest package found")
         return "jest"
      

   if (project_dir/"pyproject.toml").exists():

      content = (project_dir/"pyproject.toml").read_text(
         encoding="utf-8"
      )

      if "pytest" in content:
         print("python package found")
         return "pytest"

   return "unknown"


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

