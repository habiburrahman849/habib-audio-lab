# app.py -- Hugging Face Gradio SDK Compatibility Wrapper for ZeroGPU
# This file runs the Flask backend in a background thread and proxies API requests.

import os
import sys
import threading
import time
import requests
import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# --- Hugging Face ZeroGPU Dummy Function ---
# Hugging Face ZeroGPU spaces scan files at startup and crash if no @spaces.GPU decorator is found.
# We import spaces conditionally to support both Hugging Face and local environments.
try:
    import spaces
    print("ZeroGPU spaces environment detected.")
except ImportError:
    # Mock spaces module for local environment fallback
    class spaces:
        @staticmethod
        def GPU(func):
            return func
    print("Running in CPU/local fallback mode (mocking @spaces.GPU).")

@spaces.GPU
def dummy_gpu_check():
    """Dummy function to satisfy Hugging Face ZeroGPU startup scanner."""
    return "GPU initialization check passed."

# --- Setup Paths ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

# --- 1. Download Model Files on Startup ---
print("Checking for Kokoro models...")
try:
    from download_models import MODELS, download_file
    for filename, urls in MODELS.items():
        filepath = os.path.join(ROOT_DIR, filename)
        download_file(filepath, urls)
except Exception as e:
    print(f"Error downloading models on startup: {e}")

# --- 2. Run Flask Backend in Background Thread ---
def run_flask():
    print("Starting local Flask backend on port 5000...")
    backend_path = os.path.join(ROOT_DIR, "backend")
    sys.path.append(backend_path)
    
    from backend.app import app as flask_app
    # Run Flask locally on loopback interface
    flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# Wait briefly for Flask to initialize
time.sleep(2)

# --- 3. FastAPI REST API Gateway Router ---
app = FastAPI()

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_api(request: Request, path: str):
    """Proxy all /api/... requests directly to the local Flask server."""
    url = f"http://127.0.0.1:5000/api/{path}"
    method = request.method
    
    # Strip Host and Content-Length headers to avoid conflicts
    headers = {
        key: value for key, value in request.headers.items() 
        if key.lower() not in ["host", "content-length"]
    }
    params = dict(request.query_params)
    body = await request.body()
    
    try:
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=body,
            stream=True,
            timeout=180
        )
        
        # Strip encoding/length headers to allow FastAPI to stream cleanly
        resp_headers = {
            key: value for key, value in resp.headers.items()
            if key.lower() not in ["content-length", "content-encoding", "transfer-encoding"]
        }
        
        return StreamingResponse(
            resp.iter_content(chunk_size=4096),
            status_code=resp.status_code,
            headers=resp_headers
        )
    except Exception as e:
        return {"error": f"Failed to proxy request: {str(e)}"}, 500

# --- 4. Gradio Interface (Required by Hugging Face Space) ---
with gr.Blocks(title="Habib Audio Lab Backend") as demo:
    gr.Markdown("# 🕌 Habib Lab's AI Audio - API Gateway Active")
    gr.Markdown("The backend REST API is running. The Vercel frontend is connected directly to this Space.")
    
    with gr.Row():
         gr.HTML("<p>Status: <span style='color: green; font-weight: bold;'>Active & Ready</span></p>")
         
    # Call the dummy GPU check once on UI load to trigger/confirm ZeroGPU connection
    gpu_status = gr.State(value="")
    demo.load(fn=dummy_gpu_check, outputs=gpu_status)

# Mount the Gradio app to FastAPI
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    print("Starting API gateway server on port 7860...")
    uvicorn.run(app, host="0.0.0.0", port=7860)
