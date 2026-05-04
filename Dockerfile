FROM node:20-bookworm-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_STATIC_DIR=/app/static

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/app /app/app
COPY --from=frontend-build /app/frontend/dist /app/static

RUN mkdir -p /data/backups

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import base64, os, urllib.request; req=urllib.request.Request('http://127.0.0.1:8080/api/health'); u=os.getenv('APP_BASIC_AUTH_USER'); p=os.getenv('APP_BASIC_AUTH_PASSWORD'); req.add_header('Authorization', 'Basic ' + base64.b64encode(f'{u}:{p}'.encode()).decode()) if u and p else None; urllib.request.urlopen(req, timeout=5)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
