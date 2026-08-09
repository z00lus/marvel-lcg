FROM node:22-bookworm-slim AS frontend

WORKDIR /build
COPY public/js ./public/js

RUN npx --yes --package=typescript tsc --project public/js/tsconfig.json

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /build/public/js ./public/js

EXPOSE 2345

CMD ["python", "-u", "main.py"]
