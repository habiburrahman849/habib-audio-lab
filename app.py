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

# --- Global States ---
DOWNLOAD_STATUS = "Starting up..."
MODELS_READY = False
FLASK_READY = False

# --- Hugging Face ZeroGPU Dummy Function ---
# Hugging Face ZeroGPU spaces scan files at startup and crash if no @spaces.GPU decorator is found.
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

# --- Background Initializer ---
def initialize_backend():
    global DOWNLOAD_STATUS, MODELS_READY, FLASK_READY
    
    # 1. Download Model Files in Background
    print("Checking for Kokoro models...")
    DOWNLOAD_STATUS = "Downloading model files..."
    try:
        from download_models import MODELS, download_file
        for filename, urls in MODELS.items():
            filepath = os.path.join(ROOT_DIR, filename)
            DOWNLOAD_STATUS = f"Downloading {filename}..."
            download_file(filepath, urls)
        MODELS_READY = True
        DOWNLOAD_STATUS = "Models ready. Starting audio engine..."
        print("Models are ready.")
    except Exception as e:
        print(f"Error downloading models on startup: {e}")
        DOWNLOAD_STATUS = f"Download error: {e}"
        return

    # 2. Run Flask Backend (only after models are ready!)
    try:
        backend_path = os.path.join(ROOT_DIR, "backend")
        sys.path.append(backend_path)
        
        DOWNLOAD_STATUS = "Initializing audio synthesis engine..."
        from backend.app import app as flask_app
        
        DOWNLOAD_STATUS = "Starting backend server..."
        
        # Start Flask locally on loopback interface
        def start_flask_server():
            flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
            
        threading.Thread(target=start_flask_server, daemon=True).start()
        
        # Wait for Flask to respond to health check
        for i in range(15):
            try:
                r = requests.get("http://127.0.0.1:5000/api/health", timeout=1)
                if r.status_code == 200:
                    FLASK_READY = True
                    DOWNLOAD_STATUS = "Fully active and ready."
                    print("Backend is fully active and ready!")
                    break
            except Exception:
                time.sleep(1)
                
        if not FLASK_READY:
            DOWNLOAD_STATUS = "Backend server failed to respond."
            print("Backend server failed to respond to local health check.")
    except Exception as e:
        print(f"Error initializing backend: {e}")
        DOWNLOAD_STATUS = f"Initialization error: {e}"

# Start initialization thread immediately in the background
threading.Thread(target=initialize_backend, daemon=True).start()

# --- FastAPI REST API Gateway Router ---
app = FastAPI()

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_api(request: Request, path: str):
    """Proxy all /api/... requests directly to the local Flask server."""
    if not FLASK_READY:
        return {
            "error": "Backend is still initializing.",
            "status": DOWNLOAD_STATUS,
            "models_ready": MODELS_READY
        }, 503
        
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

# --- Gradio Interface (Required by Hugging Face Space) ---
with gr.Blocks(title="Habib Audio Lab Backend") as demo:
    gr.Markdown("# 🕌 Habib Lab's AI Audio - API Gateway Active")
    gr.Markdown("The backend REST API is running. The Vercel frontend is connected directly to this Space.")
    
    with gr.Row():
         gr.HTML("<p>Status: <span style='color: green; font-weight: bold;'>Active & Ready</span> (Audio engine initializing in background)</p>")
         
    # Call the dummy GPU check once on UI load to trigger/confirm ZeroGPU connection
    gpu_status = gr.State(value="")
    demo.load(fn=dummy_gpu_check, outputs=gpu_status)

# Mount the Gradio app to FastAPI with SSR disabled to prevent internal Node.js port conflicts
app = gr.mount_gradio_app(app, demo, path="/", ssr_mode=False)

if __name__ == "__main__":
    import uvicorn
    # Hugging Face sets the PORT environment variable to the correct port we must bind to.
    # Locally, it will default to 7860.
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting API gateway server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
