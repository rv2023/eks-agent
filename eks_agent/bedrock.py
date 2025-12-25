import json
import boto3

def get_bedrock_client():
    return boto3.client("bedrock-runtime")

def ask_claude(system_prompt: str, user_prompt: str) -> str:
    client = get_bedrock_client()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt}
                ]
            }
        ],
    }

    response = client.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )

    raw_body = response["body"].read()
    decoded = json.loads(raw_body)

    return extract_text(decoded)

def extract_text(decoded_response: dict) -> str:
    if decoded_response.get("type") != "message":
        raise RuntimeError("Unexpected Bedrock response format")

    content = decoded_response.get("content", [])

    texts = []
    for block in content:
        if block.get("type") == "text":
            texts.append(block.get("text", ""))

    if not texts:
        raise RuntimeError(f"No text returned by model: {decoded_response}")

    return "\n".join(texts)