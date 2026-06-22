from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "open_english_wordnet"
URL = "https://en-word.net/static/english-wordnet-2025.xml.gz"
OUTPUT = RAW_DIR / "english-wordnet-2025.xml.gz"
MANIFEST = RAW_DIR / "manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not OUTPUT.exists():
        print(f"Downloading {URL}")
        urllib.request.urlretrieve(URL, OUTPUT)
    else:
        print(f"Using existing {OUTPUT}")

    manifest = {
        "source_id": "open_english_wordnet_2025_xml",
        "source_name": "Open English WordNet",
        "source_version": "2025 XML",
        "source_url": URL,
        "license": "CC-BY 4.0",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "file": str(OUTPUT.relative_to(ROOT)),
        "sha256": sha256(OUTPUT),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {MANIFEST}")


if __name__ == "__main__":
    main()
