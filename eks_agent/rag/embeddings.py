# eks_agent/rag/embeddings.py

from typing import List
import json
import boto3


class BedrockEmbeddingProvider:
    """
    Minimal, deterministic embedding provider.
    No retries, no magic.
    """

    def __init__(self, model_id: str, region: str = "us-east-1"):
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def embed_text(self, text: str) -> List[float]:
        resp = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps({"inputText": text}),
            accept="application/json",
            contentType="application/json",
        )
        body = json.loads(resp["body"].read())
        return body["embedding"]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]