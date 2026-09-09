from pathlib import Path
import subprocess

import shutil

from frameworks.base import TestFramework


class JestAdapter(TestFramework):

    def discover_tests(self, project_path) -> list[str]:

        project_dir = Path(project_path).resolve()

        test_file = []

        for pattern in [
            "**/*.test.js",
            "**/*.test.ts",
            "**/*.spec.js",
            "**/*.spec.ts"
        ]:

            test_file.extend(project_dir.rglob(pattern))

            return [
                str(path.relative_to(project_dir)) for path in test_file
            ]
    

    def run_test(self,project_path, test_path) -> dict:

        print("test path called : " + test_path)

        project_dir = Path(project_path).resolve()

        npx = shutil.which("npx.cmd")

        if not npx:
            return {
                "exit_code" : 1,
                "stdout" :"",
                "stderr" : "npx.cmd not found"
            }

        result = subprocess.run(
            [npx,"jest",test_path],
            cwd=project_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return {
            "exit" : result.returncode,
            "stdout" : result.stdout,
            "stderr" : result.stderr
        }

    def read_test_file(self, project_path, test_path) -> str:
        project_dir = Path(project_path).resolve()

        test_file = project_dir / test_path

        if not test_file.exists:
            return f"Test file '{test_file}' does not exist"

        return test_file.read_text(encoding="utf-8")