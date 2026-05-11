import os
import random
from datetime import datetime
from pathlib import Path

import boto3

LOT_ID = 2

AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("BUCKET_NAME")
IMAGES_FOLDER = os.getenv("IMAGES_FOLDER")


def pick_random_image() -> Path:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    images = [p for p in Path(IMAGES_FOLDER).iterdir() if p.suffix.lower() in exts]
    if not images:
        raise FileNotFoundError(f"Không tìm thấy ảnh trong '{IMAGES_FOLDER}'")
    return random.choice(images)


def build_s3_key(local_path: Path) -> str:
    ext = local_path.suffix.lower()
    ts = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    return f"{LOT_ID}/camera_{ts}{ext}"


def upload_to_s3(local_path: Path) -> str:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    key = build_s3_key(local_path)
    s3.upload_file(str(local_path), BUCKET_NAME, key)
    return key