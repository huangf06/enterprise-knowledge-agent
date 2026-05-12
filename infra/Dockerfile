FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.8

COPY pyproject.toml uv.lock /app/
RUN uv sync --no-dev --frozen

COPY src /app/src
COPY prompts /app/prompts
COPY config /app/config
COPY data /app/data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.main:api", "--host", "0.0.0.0", "--port", "8000"]
