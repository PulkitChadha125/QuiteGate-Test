from pathlib import Path
import hashlib
import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"


def load_config(path=None) -> dict:
    p = Path(path) if path else DEFAULT_CONFIG
    with open(p, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_hash"] = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    return cfg
