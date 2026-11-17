"""QuietGate command line.

python -m quietgate.cli fetch-models   # openWakeWord + Silero VAD + Vosk EN/KO small models
python -m quietgate.cli make-data      # synthetic scenes + data/labels.json (needs internet once, for edge-tts)
python -m quietgate.cli eval           # baseline vs QuietGate -> results/report.md
python -m quietgate.cli live           # microphone demo (use headphones)
python -m quietgate.cli serve --port 6060   # web page for the client
"""
import argparse
import io
import sys
import urllib.request
import zipfile

from .config import ROOT, load_config

VOSK_MODELS = ["vosk-model-small-en-us-0.15", "vosk-model-small-ko-0.22"]


def fetch_models():
    import openwakeword.utils as u
    u.download_models(model_names=["hey_jarvis"])
    mdir = ROOT / "models"
    mdir.mkdir(exist_ok=True)
    for m in VOSK_MODELS:
        if (mdir / m).exists():
            print(f"ok   {m}")
            continue
        print(f"get  {m} ...", flush=True)
        data = urllib.request.urlopen(f"https://alphacephei.com/vosk/models/{m}.zip").read()
        zipfile.ZipFile(io.BytesIO(data)).extractall(mdir)
    print("models ready")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="quietgate")
    ap.add_argument("--config", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch-models")
    sub.add_parser("make-data")
    e = sub.add_parser("eval")
    e.add_argument("--workers", type=int, default=4)
    sub.add_parser("live")
    s = sub.add_parser("serve")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=6060)
    a = ap.parse_args(argv)

    if a.cmd == "fetch-models":
        fetch_models()
    elif a.cmd == "make-data":
        from .scenarios import make_data
        meta = make_data(load_config(a.config))
        sc = meta["scenes"]
        print(f"built {len(sc)} scenes, {sum(s['duration'] for s in sc)/60:.1f} min, "
              f"{sum(len(s['calls']) for s in sc)} calls, {sum(len(s['stops']) for s in sc)} stops")
    elif a.cmd == "eval":
        from .run_eval import run
        print(run(a.config, a.workers))
    elif a.cmd == "live":
        from .live import run_live
        run_live(load_config(a.config))
    elif a.cmd == "serve":
        sys.path.insert(0, str(ROOT))
        from app import launch
        launch(a.host, a.port)


if __name__ == "__main__":
    main()
