#!/bin/bash
# Start both the FastAPI backend and Streamlit frontend.
# FastAPI runs in the background; Streamlit runs in the foreground
# (so Docker can track the main process).

# Start the FastAPI server on port 8000 (background)
uvicorn agent.app:app --host 0.0.0.0 --port 8000 &

# Start the Streamlit frontend on port 8501 (foreground)
# --server.headless=true  disables the "open browser" prompt
# --server.address=0.0.0.0  listens on all interfaces (needed in Docker)
# --server.baseUrlPath=/chat  serves Streamlit at /chat/* when behind the ALB
streamlit run src/agent/streamlit_app.py \
  --server.port 8501 \
  --server.headless true \
  --server.address 0.0.0.0 \
  --server.baseUrlPath /chat
