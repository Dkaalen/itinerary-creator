"""Download the approved DM Sans weights from the official Google Fonts source."""
from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/googlefonts/dm-fonts/main/Sans/fonts/ttf"
FILES = {
    "DMSans-Regular.ttf": "DMSans-Regular.ttf",
    "DMSans-Medium.ttf": "DMSans-Medium.ttf",
    "DMSans-SemiBold.ttf": "DMSans-SemiBold.ttf",
    "DMSans-Bold.ttf": "DMSans-Bold.ttf",
}
TARGET = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "dm-sans"


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, source_name in FILES.items():
        data = urlopen(f"{BASE}/{source_name}", timeout=30).read()
        (TARGET / name).write_bytes(data)
    license_text = urlopen("https://raw.githubusercontent.com/googlefonts/dm-fonts/main/Sans/OFL.txt", timeout=30).read()
    (TARGET / "OFL.txt").write_bytes(license_text)
    print(f"Installed DM Sans in {TARGET}")


if __name__ == "__main__":
    main()
