FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies (if needed)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md* ./
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
