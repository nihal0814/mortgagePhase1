import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(BASE_DIR / "uploads"))).resolve()
POLICY_UPLOADS_DIR = Path(os.getenv("POLICY_UPLOADS_DIR", str(BASE_DIR / "policy_uploads"))).resolve()
POLICY_INDEX_PATH = Path(os.getenv("POLICY_INDEX_PATH", str(BASE_DIR / "policy_index.json"))).resolve()
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(15 * 1024 * 1024)))
MAX_POLICY_UPLOAD_SIZE = int(os.getenv("MAX_POLICY_UPLOAD_SIZE", str(10 * 1024 * 1024)))
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
OCR_DPI = int(os.getenv("OCR_DPI", "200"))
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "").strip()
NVIDIA_USE_JSON_MODE = os.getenv("NVIDIA_USE_JSON_MODE", "true").lower() == "true"
NVIDIA_TIMEOUT_SECONDS = float(os.getenv("NVIDIA_TIMEOUT_SECONDS", "45"))
NEMOTRON_MAX_INPUT_CHARS = int(os.getenv("NEMOTRON_MAX_INPUT_CHARS", "24000"))
POLICY_CHUNK_SIZE = int(os.getenv("POLICY_CHUNK_SIZE", "1200"))
POLICY_CHUNK_OVERLAP = int(os.getenv("POLICY_CHUNK_OVERLAP", "150"))
POLICY_EMBEDDING_DIMENSIONS = int(os.getenv("POLICY_EMBEDDING_DIMENSIONS", "256"))
POLICY_TOP_K = int(os.getenv("POLICY_TOP_K", "5"))
FINANCIAL_TOLERANCE_PERCENT = float(os.getenv("FINANCIAL_TOLERANCE_PERCENT", "2"))
MAX_DTI = float(os.getenv("MAX_DTI")) if os.getenv("MAX_DTI") else None
MAX_LTV = float(os.getenv("MAX_LTV")) if os.getenv("MAX_LTV") else None
MIN_CREDIT_SCORE = int(os.getenv("MIN_CREDIT_SCORE")) if os.getenv("MIN_CREDIT_SCORE") else None
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-development-secret")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_CATEGORIES = {
    "Salary Slip",
    "Bank Statement",
    "Income Tax Return",
    "Identity Proof",
    "Property Document",
    "Other",
}
