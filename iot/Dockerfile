FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 mecaniqa \
    && useradd --uid 10001 --gid mecaniqa --no-create-home mecaniqa
COPY --chown=mecaniqa:mecaniqa mecaniqa_iot ./mecaniqa_iot
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1
CMD ["python", "-m", "mecaniqa_iot"]
