from pathlib import Path
import sys


import subprocess

from frameworks.base import TestFramework


class PytestAdapter(TestFramework):

    def discover_tests(self, project_path:str) ->list[str]:

        project_dir = Path(project_path).resolve()

        tests_dir = project_dir / "tests"

        if not tests_dir.exists():
            return []


        return [
            str(path.relative_to(project_dir)) for path in tests_dir.rglob("test_*.py")
        ]


    def run_test(self, project_path:str, test_path:str) -> dict:

        project_dir = Path(project_path).resolve()

        test_file = project_dir / test_path

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(test_file)
            ],
            cwd = project_dir,
            capture_output=True,
            text=True
        )

        return {
            "exit_code" : result.returncode,
            "stdout" : result.stdout,
            "stderr" : result.stderr
        }


    def read_test_file(self, project_path:str, test_path:str) -> str:

        project_dir = Path(project_path).resolve()

        test_file = project_dir/test_path

        if not test_file.exists():
            return f"Test file '{test_path}' does not exist "

        return test_file.read_text(encoding="utf-8")

