"""
download_models.py -- Habib Lab's TTS
Downloads Kokoro ONNX model files with retry support.
Run once: python download_models.py
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

# Model files and their download URLs (primary = HuggingFace CDN, fallback = GitHub)
MODELS = {
    "kokoro-v0_19.onnx": [
        "https://huggingface.co/thewh1teagle/Kokoro/resolve/main/kokoro-v0_19.onnx",
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx",
    ],
    "voices.bin": [
        "https://huggingface.co/thewh1teagle/Kokoro/resolve/main/voices.bin",
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin",
    ],
}

CHUNK_SIZE = 1024 * 256  # 256 KB chunks
MAX_RETRIES = 5


def download_file(filename, urls):
    if os.path.exists(filename):
        size = os.path.getsize(filename)
        print(f"  [OK] Already exists: {filename} ({size/1024/1024:.1f} MB)")
        return True

    for attempt, url in enumerate(urls, 1):
        source = "HuggingFace" if attempt == 1 else "GitHub"
        print(f"\n  Trying {source}: {filename}")

        for retry in range(MAX_RETRIES):
            try:
                import urllib.request
                import urllib.error

                headers = {"User-Agent": "Mozilla/5.0"}
                req = urllib.request.Request(url, headers=headers)

                with urllib.request.urlopen(req, timeout=30) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    start = time.time()

                    with open(filename, "wb") as f:
                        while True:
                            chunk = resp.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            elapsed = time.time() - start
                            speed = downloaded / elapsed / 1024 / 1024 if elapsed > 0 else 0
                            if total:
                                pct = downloaded * 100 // total
                                bar = "#" * (pct // 5) + "." * (20 - pct // 5)
                                print(
                                    f"\r  [{bar}] {pct:3d}% "
                                    f"{downloaded/1024/1024:6.1f}/{total/1024/1024:.1f} MB "
                                    f"@ {speed:.1f} MB/s",
                                    end="", flush=True
                                )
                            else:
                                print(f"\r  {downloaded/1024/1024:.1f} MB @ {speed:.1f} MB/s",
                                      end="", flush=True)

                    print(f"\n  [DONE] Saved: {filename}")
                    return True

            except Exception as e:
                print(f"\n  [RETRY {retry+1}/{MAX_RETRIES}] Error: {e}")
                if os.path.exists(filename):
                    os.remove(filename)
                time.sleep(2 * (retry + 1))

    print(f"  [FAIL] Could not download {filename}")
    return False


if __name__ == "__main__":
    print("=" * 55)
    print("  Habib Lab's TTS -- Model Downloader")
    print("  Powered by Habib Brains")
    print("=" * 55)

    all_ok = True
    for filename, urls in MODELS.items():
        ok = download_file(filename, urls)
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("  All models ready! Run: python app.py")
    else:
        print("  Some downloads failed. Please try again.")
    print("=" * 55)
