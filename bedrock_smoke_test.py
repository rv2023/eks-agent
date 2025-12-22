import json
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

prompt = "Say OK if you receive this message."

payload = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 50,
    "temperature": 0,
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]
}

response = client.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps(payload).encode("utf-8"),
    contentType="application/json",
    accept="application/json"
)

print(response["body"].read().decode("utf-8"))
