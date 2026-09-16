from __future__ import annotations
import importlib.util, subprocess, sys, os, time, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def ensure(package, pip_name=None):
    if importlib.util.find_spec(package) is None:
        name = pip_name or package
        print(f"Installing {name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", name])

ensure("streamlit")
ensure("pandas")

port = os.environ.get("SETDS_PORT", "8501")
url = f"http://localhost:{port}"

print("\nSETDS запускается…")
print(f"Если браузер не открылся автоматически: {url}\n")

try:
    webbrowser.open(url)
except Exception:
    pass

os.chdir(ROOT)
subprocess.call([
    sys.executable, "-m", "streamlit", "run", "app.py",
    "--server.port", port,
    "--server.address", "localhost",
    "--browser.gatherUsageStats", "false",
])
