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
COPY data /app/data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.main:api", "--host", "0.0.0.0", "--port", "8000"]
