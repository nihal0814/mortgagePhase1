import json
import math
from pathlib import Path
from threading import Lock
from typing import Any

from config import POLICY_INDEX_PATH
from services.embeddings import embed_text


_lock = Lock()


def _read() -> dict[str, Any]:
    if not POLICY_INDEX_PATH.is_file():
        return {"vectors": {}}
    try:
        return json.loads(POLICY_INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"vectors": {}}


def _write(data: dict[str, Any]) -> None:
    POLICY_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    POLICY_INDEX_PATH.write_text(json.dumps(data), encoding="utf-8")


def add_chunks(chunks: list[dict[str, Any]]) -> None:
    with _lock:
        data = _read()
        for chunk in chunks:
            data["vectors"][chunk["chunk_id"]] = {
                "vector": embed_text(chunk["text"]),
                "policy_id": chunk["policy_id"],
                "document_name": chunk["document_name"],
                "page_number": chunk.get("page_number"),
                "section": chunk.get("section"),
                "text": chunk["text"],
            }
        _write(data)


def delete_policy(policy_id: str) -> None:
    with _lock:
        data = _read()
        data["vectors"] = {key: value for key, value in data["vectors"].items() if value["policy_id"] != policy_id}
        _write(data)


def search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    query_vector = embed_text(query)
    results = []
    for chunk_id, value in _read()["vectors"].items():
        score = sum(left * right for left, right in zip(query_vector, value["vector"]))
        results.append({**value, "chunk_id": chunk_id, "similarity": round(score, 4)})
    return sorted(results, key=lambda item: item["similarity"], reverse=True)[:top_k]
