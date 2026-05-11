import json
import os
import time
import urllib.request
import urllib.error
import boto3

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
LAMBDA_API_KEY = os.environ["LAMBDA_API_KEY"]
SLOTS_UPDATE_URL = os.getenv(
    "SLOTS_UPDATE_URL",
    "http://localhost:8080/api/slots/update",
)

sqs = boto3.client("sqs", region_name=AWS_REGION)


def post_update(payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SLOTS_UPDATE_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": LAMBDA_API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()  # raises on non-2xx automatically


def main():
    while True:
        resp = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            VisibilityTimeout=90,
        )
        msgs = resp.get("Messages", [])
        if not msgs:
            continue

        msg = msgs[0]
        receipt = msg["ReceiptHandle"]
        body = msg["Body"]

        try:
            payload = json.loads(body)
            # payload expected: { lot_id, image_key, slots: { "A1": "free|occupied", ... } }
            post_update(payload)
            sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt)
        except Exception:
            time.sleep(1)


if __name__ == "__main__":
    main()