FROM ghcr.io/astral-sh/uv:0.11.8 AS uv

FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY main.py ./

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "python", "main.py"]
