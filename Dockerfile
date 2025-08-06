FROM python:3.11-slim
WORKDIR /app

# Install system dependencies needed for PyInstaller
RUN apt-get update && apt-get install -y binutils && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install -r requirements.txt
RUN python build.py