FROM python:3.12-slim

WORKDIR /app

# Install uv for fast installs
RUN pip install uv --no-cache-dir

COPY pyproject.toml .
RUN uv pip install --system fastapi "uvicorn[standard]" pydantic pandas numpy httpx python-dateutil

COPY app/ ./app/
COPY data/ ./data/

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
