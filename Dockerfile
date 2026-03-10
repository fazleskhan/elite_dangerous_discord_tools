FROM python:3.13-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Ensure the runtime log directory exists even before first write.
RUN addgroup --system appuser \
    && adduser --system --ingroup appuser --home /app appuser \
    && mkdir -p /app/logs/archive \
    && chown -R appuser:appuser /app


COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY . /app

USER appuser

CMD ["python", "src/discord_runner.py"]
