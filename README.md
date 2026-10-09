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

Choose another project directory with:

```powershell
python -m app.app --project-path path\to\project
```

The agent prints a JSON result. When a validated patch is proposed, it displays a unified diff and asks for explicit approval before applying it. Projects can use pytest or Jest. Jest projects need a local Jest installation in that project; the agent does not download packages while validating. A Groq key is only needed if test failures need LLM analysis.

For automatic proposal validation, add a `qa-agent-policy.json` to the target project with path globs under `normal_bug_paths` and `business_requirement_paths`. The bundled demo policy is an example. Unclassified paths are suggestion-only, and business-sensitive proposals always require owner approval.

## Tests

Run the agent's tests from the repository root:

```powershell
python -m pytest
```

## Current scope

This is a local learning project, not a hosted service. It never applies a patch without explicit approval. A simple Streamlit interface can be added after the CLI workflow is stable; deployment configuration should follow the chosen hosting target and its secret-management approach.

See [PROJECT_WALKTHROUGH.md](PROJECT_WALKTHROUGH.md) for the code and LangGraph flow explained step by step.