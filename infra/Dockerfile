FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.8

# pyproject.toml has `readme = "README.md"`, so hatchling needs the README in
# the build context when `uv sync` installs the local package. Copy it now
# even though it changes more often than the lockfile; it is small.
COPY pyproject.toml uv.lock README.md /app/
RUN uv sync --no-dev --frozen

COPY src /app/src
COPY prompts /app/prompts
COPY config /app/config
COPY scripts /app/scripts
COPY data /app/data

# Regenerate synthetic data at build time so the image is self-contained.
# data/synthetic is gitignored (and dockerignored), so we must produce it here
# instead of relying on the developer's local state. seed=42 is byte-deterministic.
RUN uv run python scripts/generate_data.py --seed 42 --output /app/data/synthetic

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.main:api", "--host", "0.0.0.0", "--port", "8000"]
