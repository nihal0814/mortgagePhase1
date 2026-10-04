from sqlalchemy import select
from sqlalchemy.orm import Session

from models.policy import Policy
from services.vector_store import search


def retrieve_policy(query: str, db: Session, top_k: int = 5) -> list[dict]:
    active_ids = {policy.id for policy in db.scalars(select(Policy).where(Policy.status == "Active")).all()}
    return [result for result in search(query, top_k) if result["policy_id"] in active_ids and result["similarity"] >= 0.05]
