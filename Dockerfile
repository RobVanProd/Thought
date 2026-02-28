FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir \
    fastapi==0.116.1 \
    uvicorn==0.35.0 \
    pydantic==2.12.5 \
    numpy==2.3.3

ENV THOUGHT_DB_PATH=/data/tms.sqlite
ENV THOUGHT_EMBED_DIM=384

EXPOSE 8000

CMD ["uvicorn", "memory_service:app", "--host", "0.0.0.0", "--port", "8000"]

