import base64
import hashlib
import json
import os
import boto3
import urllib.request

REGION = "us-east-1"
GEMINI_MODEL = "gemini-3.1-flash-lite"

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]

s3 = boto3.client("s3", region_name=REGION)
sqs = boto3.client("sqs", region_name=REGION)

# Long, detailed prompt (same intent as your original Lambda).
PROMPT = """
You are a parking lot monitoring assistant.
Analyze the provided parking lot image and detect the occupancy status of each slot.

Rules:
- A slot is "occupied" if a vehicle is present inside that slot (car, van, motorcycle clearly within the slot boundaries).
- A slot is "free" if no vehicle is detected in that slot.
- Slot IDs painted on the ground may be partially hidden, blurred, or at an angle. Use visible labels nearby,
  lane layout, and spacing to infer the correct label for each bay. Stay consistent with a typical grid.

You must cover every slot in this lot layout: A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10.
Each of those strings must appear exactly once as a key in "slots". Use the same spelling and casing as listed.

Return ONLY a valid JSON object. Do not wrap it in markdown. Do not add any explanation before or after the JSON.
Use exactly this structure and key names:

{
    "timestamp": "<ISO8601 datetime string in UTC>",
    "total_slots": 20,
    "occupied_count": <integer>,
    "free_count": <integer>,
    "slots": {
        "A1": "free",
        "A2": "occupied",
        "A3": "free",
        "A4": "free",
        "A5": "free",
        "A6": "free",
        "A7": "free",
        "A8": "free",
        "A9": "free",
        "A10": "free",
        "B1": "free",
        "B2": "free",
        "B3": "free",
        "B4": "free",
        "B5": "free",
        "B6": "free",
        "B7": "free",
        "B8": "free",
        "B9": "free",
        "B10": "free"
    }
}

Constraints on values:
- Every value inside "slots" must be exactly the lowercase word "free" or "occupied" (do not use "empty", "vacant", or other synonyms).
- "occupied_count" must equal the number of entries in "slots" whose value is "occupied".
- "free_count" must equal the number of entries whose value is "free".
- "total_slots" must be 20 and must match the number of keys in "slots".
""".strip()


def lot_id_from_key(image_key: str) -> int:
    key = (image_key or "").strip().lstrip("/")
    if not key:
        raise ValueError("empty S3 key")
    if key.split("/")[0].isdigit():
        return int(key.split("/")[0])
    head = key.split("/")[-1].split("_")[0]
    if head.isdigit():
        return int(head)
    raise ValueError(f"lot_id not in key: {image_key!r} — use e.g. 2/photo.jpg or 2_photo.jpg")


def mime_from_key(key: str) -> str:
    k = key.lower().split("/")[-1]
    if k.endswith(".png"):
        return "image/png"
    if k.endswith(".webp"):
        return "image/webp"
    if k.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def strip_code_fences(text: str) -> str:
    t = text.strip()
    for p in ("```json", "```JSON", "```"):
        if t.startswith(p):
            t = t[len(p) :].strip()
    if t.endswith("```"):
        t = t[:-3].strip()
    return t


def lambda_handler(event, context):
    r = event["Records"][0]
    bucket = r["s3"]["bucket"]["name"]
    image_key = r["s3"]["object"]["key"]
    lot_id = lot_id_from_key(image_key)

    img = s3.get_object(Bucket=bucket, Key=image_key)["Body"].read()
    b64 = base64.b64encode(img).decode("utf-8")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(
            {
                "contents": [
                    {
                        "parts": [
                            {"text": PROMPT},
                            {"inline_data": {"mime_type": mime_from_key(image_key), "data": b64}},
                        ]
                    }
                ]
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as res:
        api = json.loads(res.read().decode("utf-8"))
    text = api["candidates"][0]["content"]["parts"][0]["text"]
    text = strip_code_fences(text)
    data = json.loads(text)

    slots = {}
    for k, v in data["slots"].items():
        v = str(v).strip().lower()
        if v == "empty":
            v = "free"
        if v not in ("free", "occupied"):
            raise ValueError(f"invalid status for {k!r}: {v!r}")
        slots[str(k).strip()] = v

    msg = {"lot_id": lot_id, "image_key": image_key, "slots": slots}
    body = json.dumps(msg)

    kwargs = {"QueueUrl": SQS_QUEUE_URL, "MessageBody": body}
    if SQS_QUEUE_URL.endswith(".fifo"):
        kwargs["MessageGroupId"] = str(lot_id)
        kwargs["MessageDeduplicationId"] = hashlib.sha256(
            f"{image_key}:{context.aws_request_id}".encode()
        ).hexdigest()[:128]
    sqs.send_message(**kwargs)

    return {"statusCode": 200, "body": body}
