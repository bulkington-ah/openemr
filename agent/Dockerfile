# Dockerfile for the OpenEMR AI Agent
#
# Builds a container that runs both:
# - FastAPI server (port 8000) — the agent's HTTP API
# - Streamlit frontend (port 8501) — the chat UI
#
# The CI/CD pipeline builds this image, pushes it to AWS ECR, and deploys
# it to EC2 where it runs alongside OpenEMR.
#
# Build:   docker build -t openemr-agent .
# Run:     docker run -p 8000:8000 -p 8501:8501 --env-file .env openemr-agent

FROM python:3.12-slim

# Prevent Python from writing .pyc bytecode files and enable unbuffered output
# (so logs appear immediately in Docker)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy source code, build config, and startup script
COPY pyproject.toml .
COPY src/ src/
COPY start.sh .

# Install the package (includes dependencies)
# Source must be present before install so hatchling can find src/agent/
RUN pip install --no-cache-dir .

# FastAPI on 8000, Streamlit on 8501
EXPOSE 8000 8501

# Start both services via the startup script
CMD ["bash", "start.sh"]
