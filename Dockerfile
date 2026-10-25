FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y python3 python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY agent ./agent
COPY app ./app
COPY frameworks ./frameworks
COPY README.md ./README.md
COPY PROJECT_WALKTHROUGH.md ./PROJECT_WALKTHROUGH.md

RUN mkdir -p /workspace && chown node:node /workspace
USER node

ENV QA_AGENT_UAT_ROOT=/workspace

CMD ["python", "-m", "app.app", "--environment", "uat", "--project-path", "/workspace/demo-project"]