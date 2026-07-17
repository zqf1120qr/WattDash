FROM python:3.10-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# 强制将 Debian 软件源替换为阿里云国内源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null || true

# Install Chromium, dependencies for headless mode, and Chinese fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /workspace/backend

# Copy dependency requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# Copy source code
COPY app/ ./app/

# Create directory for token storage and database persistence
RUN mkdir -p /workspace/backend/app/database && chmod 777 /workspace/backend/app/database

# Set environment variables for DrissionPage
ENV CHROMIUM_PATH=/usr/bin/chromium
ENV CHROMIUM_USER_DATA=/tmp/chromium_user_data
ENV SECRET_KEY=super-secret-jwt-key-change-in-production

# Expose backend port
EXPOSE 9100

# Start FastAPI application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9100"]
