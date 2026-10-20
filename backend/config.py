import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "documents"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "pricing_copilot.db"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_INFO = {
    "title": "AI-Powered Real-Time Pricing Intelligence and Quotation Copilot for MSMEs Using RAG",
    "subtitle": "An evidence-backed decision-support system for B2B pricing and quotation workflows",
    "authors": [
        {"name": "Aryan Jha", "id": "245890206"},
        {"name": "Kunsh Mehra", "id": "245890196"},
        {"name": "Rishit Kumar Agarwal", "id": "245890302"}
    ],
    "company": "Apex Precision Fasteners & Hardware Pvt. Ltd.",
    "vertical": "Industrial Fasteners & Precision Engineering Hardware",
    "version": "1.0.0",
    "currency": "INR",
    "currency_symbol": "₹"
}

# Optional external LLM API keys (can also be configured dynamically via UI)
DEFAULT_SETTINGS = {
    "llm_provider": "local_nlp",  # options: 'local_nlp', 'gemini', 'openai', 'anthropic'
    "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    "deterministic_floor_margin": 0.09,  # 9% strict floor margin
}
