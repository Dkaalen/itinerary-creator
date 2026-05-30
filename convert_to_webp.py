from pathlib import Path
from PIL import Image

ROOT = Path(r"C:\Users\DennisKålen\Desktop\itinerary_app\image_bank_full")
QUALITY = 85

extensions = {".jpg", ".jpeg", ".png"}

converted = 0
skipped = 0
failed = 0

for image_path in ROOT.rglob("*"):
    if image_path.suffix.lower() not in extensions:
        continue

    webp_path = image_path.with_suffix(".webp")

    if webp_path.exists():
        print(f"Skipping, already exists: {webp_path}")
        skipped += 1
        continue

    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "LA"):
                img.save(webp_path, "WEBP", quality=QUALITY)
            else:
                img.convert("RGB").save(webp_path, "WEBP", quality=QUALITY)

        print(f"Converted: {image_path}")
        converted += 1

    except Exception as e:
        print(f"FAILED: {image_path}")
        print(f"Reason: {e}")
        failed += 1

print()
print("Done.")
print(f"Converted: {converted}")
print(f"Skipped: {skipped}")
print(f"Failed: {failed}")