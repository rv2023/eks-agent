import json
import boto3

class BedrockClient:
    def __init__(self, region: str):
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def invoke(self, model_id: str, body: dict) -> str:
        payload_json = json.dumps(body)
        print("\n===== BEDROCK PAYLOAD BEGIN =====")
        print(payload_json)
        print("===== BEDROCK PAYLOAD END =====\n")

        resp = self.client.invoke_model(
            modelId=model_id,
            body=payload_json.encode("utf-8"),
            contentType="application/json",
            accept="application/json",
        )

        return resp["body"].read().decode("utf-8")
