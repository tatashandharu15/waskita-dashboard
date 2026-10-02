import os

try:
    from mangum import Mangum
except Exception:
    Mangum = None

from main import app

if Mangum is not None:
    handler = Mangum(app, lifespan="off")
else:
    def handler(event, context):
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": "{\"error\": \"mangum dependency missing. Install via pip install mangum>=0.17.0\"}",
        }
