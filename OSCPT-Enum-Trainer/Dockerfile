# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8011

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY oscpt_enum_trainer.py ./

RUN useradd --system --uid 10001 --home-dir /app --no-create-home oscpt \
    && chown -R oscpt:oscpt /app
USER 10001:10001

EXPOSE 8011

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8011/health', timeout=3)" || exit 1

CMD ["python", "oscpt_enum_trainer.py"]
