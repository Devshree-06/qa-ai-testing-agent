import subprocess

from frameworks import jest_adapter as jest_adapter_module
from frameworks.jest_adapter import JestAdapter


def test_jest_runs_local_entrypoint_through_node(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    local_jest = project_dir / "node_modules" / "jest" / "bin" / "jest.js"
    local_jest.parent.mkdir(parents=True)
    local_jest.write_text("", encoding="utf-8")
    calls = []

    monkeypatch.setattr(jest_adapter_module.shutil, "which", lambda name: "/usr/bin/node")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "passed", "")

    monkeypatch.setattr(jest_adapter_module.subprocess, "run", fake_run)

    result = JestAdapter().run_test(str(project_dir), "tests/login.test.js")

    assert result["exit_code"] == 0
    assert calls[0][0] == ["/usr/bin/node", str(local_jest), "tests/login.test.js"]
    assert calls[0][1]["cwd"] == project_dir
    assert "env" in calls[0][1]