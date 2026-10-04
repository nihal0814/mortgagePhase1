import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.connection import Base, engine
from models.application import Application  # noqa: F401 - registers the model
from models.document import Document  # noqa: F401 - registers the model
from models.analysis import ApplicationAnalysis, DocumentAnalysis  # noqa: F401 - registers models
from models.financial_validation import FinancialValidation, ValidationIssue  # noqa: F401 - registers models
from models.policy import Policy, PolicyChunk  # noqa: F401 - registers models
from models.underwriting import UnderwritingEvent, UnderwritingRun  # noqa: F401 - registers models
from routes.applications import router as applications_router
from routes.documents import router as documents_router
from routes.analysis import router as analysis_router
from routes.ai import router as ai_router
from routes.financial_validation import router as financial_validation_router
from routes.policies import router as policies_router
from routes.underwriting import router as underwriting_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mortgage AI Processing API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
