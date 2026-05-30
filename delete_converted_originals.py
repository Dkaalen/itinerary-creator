from pathlib import Path

ROOT = Path(r"C:\Users\DennisKålen\Desktop\itinerary_app\image_bank_full")
extensions = {".jpg", ".jpeg", ".png"}

deleted = 0
skipped = 0

for image_path in ROOT.rglob("*"):
    if image_path.suffix.lower() not in extensions:
        continue

    webp_path = image_path.with_suffix(".webp")

    if webp_path.exists():
        print(f"Deleting: {image_path}")
        image_path.unlink()
        deleted += 1
    else:
        print(f"Skipping, no matching WebP: {image_path}")
        skipped += 1

print()
print("Done.")
print(f"Deleted: {deleted}")
print(f"Skipped: {skipped}")