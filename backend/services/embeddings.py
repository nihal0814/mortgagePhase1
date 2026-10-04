import hashlib
import math
import re

from config import POLICY_EMBEDDING_DIMENSIONS


def embed_text(text: str) -> list[float]:
    """Small dependency-free hashed word n-gram embedding for the local demo index."""
    vector = [0.0] * POLICY_EMBEDDING_DIMENSIONS
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    for index, token in enumerate(tokens):
        for feature in (token, f"{token}_{tokens[index + 1]}" if index + 1 < len(tokens) else token):
            bucket = int(hashlib.sha256(feature.encode("utf-8")).hexdigest(), 16) % POLICY_EMBEDDING_DIMENSIONS
            vector[bucket] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector
