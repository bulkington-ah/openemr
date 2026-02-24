# Dockerfile for the OpenEMR AI Agent
#
# Builds a container that runs the FastAPI server (the agent's HTTP API).
# The CI/CD pipeline builds this image, pushes it to AWS ECR, and deploys
# it to EC2 where it runs alongside OpenEMR.
#
# Build:   docker build -t openemr-agent .
# Run:     docker run -p 8000:8000 --env-file .env openemr-agent

FROM python:3.12-slim

# Prevent Python from writing .pyc bytecode files and enable unbuffered output
# (so logs appear immediately in Docker)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (this layer is cached unless pyproject.toml changes)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy the source code
COPY src/ src/

# The FastAPI server listens on port 8000
EXPOSE 8000

# Start the server. "agent.app:app" means: in the agent package, find
# app.py, and use the FastAPI instance named "app".
CMD ["uvicorn", "agent.app:app", "--host", "0.0.0.0", "--port", "8000"]
