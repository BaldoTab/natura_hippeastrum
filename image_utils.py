from __future__ import annotations

import datetime as dt
import os
import re
import uuid
from pathlib import Path

from PIL import ExifTags, Image

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass


ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".heic"}


def safe_filename(original: str) -> str:
    original = original.strip()
    original = re.sub(r"[^A-Za-z0-9._-]+", "_", original)
    stem = Path(original).stem[:60]
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXT:
        ext = ".jpg"
    return f"{stem}_{uuid.uuid4().hex}{ext}"


def save_image_and_thumbnail(
    file_bytes: bytes,
    original_filename: str,
    photos_dir: Path,
    thumbs_dir: Path,
    thumb_max_px: int = 480,
) -> tuple[str, str | None, dt.date | None]:
    photos_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    filename = safe_filename(original_filename)
    photo_path = photos_dir / filename

    with open(photo_path, "wb") as f:
        f.write(file_bytes)

    thumb_filename = None
    exif_date = None

    try:
        with Image.open(photo_path) as im:
            exif_date = _extract_exif_date(im)
            im_copy = im.copy()
            im_copy.thumbnail((thumb_max_px, thumb_max_px))
            thumb_filename = f"thumb_{Path(filename).stem}.jpg"
            thumb_path = thumbs_dir / thumb_filename
            im_copy.convert("RGB").save(thumb_path, format="JPEG", quality=85, optimize=True)
    except Exception:
        thumb_filename = None

    return filename, thumb_filename, exif_date


def _extract_exif_date(im: Image.Image) -> dt.date | None:
    try:
        exif = im.getexif()
        if not exif:
            return None
        tag_map = {v: k for k, v in ExifTags.TAGS.items()}
        for key in (tag_map.get("DateTimeOriginal"), tag_map.get("DateTime")):
            if not key:
                continue
            raw = exif.get(key)
            if not raw:
                continue
            s = str(raw)
            try:
                # EXIF typical: 2026:04:29 19:14:00
                d = dt.datetime.strptime(s[:19], "%Y:%m:%d %H:%M:%S").date()
                return d
            except Exception:
                continue
    except Exception:
        return None
    return None
