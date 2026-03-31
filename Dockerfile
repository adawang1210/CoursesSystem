FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製並安裝 Python 依賴
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 複製後端應用程式碼
COPY backend/app ./app

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "120", "--bind", "0.0.0.0:8000"]
