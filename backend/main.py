import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from database.connection import Base, engine, migrate_legacy_schema
from models.application import Application  # noqa: F401 - registers the model
from models.document import Document  # noqa: F401 - registers the model
from models.analysis import ApplicationAnalysis, DocumentAnalysis  # noqa: F401 - registers models
from models.financial_validation import FinancialValidation, ValidationIssue  # noqa: F401 - registers models
from models.policy import Policy, PolicyChunk  # noqa: F401 - registers models
from models.underwriting import UnderwritingEvent, UnderwritingRun  # noqa: F401 - registers models
from models.auth import User  # noqa: F401 - registers model
from models.review import AuditLog, DocumentRequest, ReviewIssue, ReviewNote  # noqa: F401 - registers models
from routes.applications import router as applications_router
from routes.documents import router as documents_router
from routes.analysis import router as analysis_router
from routes.ai import router as ai_router
from routes.financial_validation import router as financial_validation_router
from routes.policies import router as policies_router
from routes.underwriting import router as underwriting_router
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.review import router as review_router
from routes.audit import router as audit_router


Base.metadata.create_all(bind=engine)
migrate_legacy_schema()

app = FastAPI(title="Mortgage AI Processing API", version="1.0.0")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


app.add_middleware(SecurityHeadersMiddleware)

configured_frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
frontend_origins = list(dict.fromkeys([configured_frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(applications_router)
app.include_router(documents_router)
app.include_router(analysis_router)
app.include_router(ai_router)
app.include_router(financial_validation_router)
app.include_router(policies_router)
app.include_router(underwriting_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(review_router)
app.include_router(audit_router)
