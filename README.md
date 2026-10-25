# AI QA Testing Agent

A small command-line QA assistant that discovers supported test frameworks, runs their tests, and uses a Groq-hosted language model to analyze failures. It can propose one focused source change, validates it in a temporary project copy, and shows a diff for review before applying anything to the original project.

## Requirements

- Python 3.10 or newer
- A Groq API key for failure analysis
- Node.js and npm only when running against a Jest project

## Setup

From the repository root, create and activate a virtual environment in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Add your key to `.env`:

```text
GROQ_API_KEY=your_key_here
```

Do not commit `.env` or share its contents.

## Run

Run the bundled Python demo:

```powershell
python -m app.app
```

The CLI defaults to `--environment uat`. UAT targets must be inside `QA_AGENT_UAT_ROOT`,
which defaults to the repository's `workspace/` directory. Set that variable in the
trusted agent environment to use a different UAT project root. Selecting
`--environment production` is currently rejected before project configuration is loaded
or the agent workflow starts.

Choose another project directory with:

```powershell
python -m app.app --project-path path\to\project
```

The agent prints a JSON result. When a validated patch is proposed, it displays a unified diff and asks for explicit approval before applying it. Projects can use pytest or Jest. Jest projects need a local Jest installation in that project; the agent does not download packages while validating. A Groq key is only needed if test failures need LLM analysis.

Test subprocesses receive only the operating-system runtime variables they need by default, not the full agent environment. To pass approved non-secret values to tests, set `QA_AGENT_TEST_ENV_ALLOWLIST` in the trusted agent environment to a comma-separated list of variable names. Never allowlist credentials. This reduces accidental secret exposure but is not process or filesystem isolation; use containers for untrusted projects.

## Docker UAT

Docker Compose runs the CLI as a non-root user and mounts a host UAT workspace at `/workspace`. From the repository root, set the Groq key in the current PowerShell session when failure analysis is needed, then run:

```powershell
$env:GROQ_API_KEY = "your_key_here"
docker compose run --build --rm qa-agent
```

The default target is `workspace/demo-project`. To use a different UAT workspace root and project directory:

```powershell
$env:QA_AGENT_UAT_ROOT = "C:\path\to\uat-workspace"
$env:QA_AGENT_PROJECT_PATH = "/workspace/my-project"
docker compose run --build --rm qa-agent
```

The project directory must be inside the mounted UAT root. Jest projects must already have their local dependencies installed, including Jest, for the container's Linux/Node runtime; Windows-specific `node_modules` may not work in the Linux image. The container invokes the local Jest entry point and does not install project packages. The approval prompt is interactive, so keep the Compose command attached to a terminal. This setup is for controlled UAT testing, not a hardened sandbox for hostile code: test processes still share the container's filesystem and network access.

To exercise failure analysis and the approval prompt without changing the passing demo project, use the intentionally failing fixture in `workspace/docker-failure-demo`:

```powershell
$env:GROQ_API_KEY = "your_key_here"
$env:QA_AGENT_PROJECT_PATH = "/workspace/docker-failure-demo"
docker compose run --build --rm qa-agent
```

The single test is expected to fail, after which the agent should analyze it and present a proposed source diff. Answer `n` to verify rejection without changing the fixture. Answering `y` applies the patch to `workspace/docker-failure-demo/src/math_utils.py` through the bind mount; reset that fixture source before repeating the test.

For automatic proposal validation, add a `qa-agent-policy.json` to the target project with path globs under `normal_bug_paths` and `business_requirement_paths`. The bundled demo policy is an example. Unclassified paths are suggestion-only, and business-sensitive proposals always require owner approval.

## Tests

Run the agent's tests from the repository root:

```powershell
python -m pytest
```

## Current scope

This is a local learning project, not a hosted service. It never applies a patch without explicit approval. A simple Streamlit interface can be added after the CLI workflow is stable; deployment configuration should follow the chosen hosting target and its secret-management approach.

See [PROJECT_WALKTHROUGH.md](PROJECT_WALKTHROUGH.md) for the code and LangGraph flow explained step by step.