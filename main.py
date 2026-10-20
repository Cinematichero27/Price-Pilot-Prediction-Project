import os
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from pydantic import BaseModel

from backend.config import PROJECT_INFO, BASE_DIR, DOCS_DIR, UPLOADS_DIR, DEFAULT_SETTINGS
from backend.database import get_connection, init_db, log_audit
from backend.seed_data import seed_database
from backend.pricing_engine import pricing_engine
from backend.rag_engine import rag_engine
from backend.copilot_service import copilot
from backend.pdf_generator import generate_quotation_pdf
from backend.analytics_service import analytics_service
from backend.ingestion_service import ingestion_service
from backend.evaluation_service import evaluation_service

# Initialize Database and seed initial data if not already present
init_db()
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) as c FROM products")
if cursor.fetchone()["c"] == 0:
    seed_database()
conn.close()

app = FastAPI(
    title="PricePilot AI - B2B Pricing Intelligence and Quotation Copilot",
    description="Evidence-Driven Pricing and Quotation Intelligence System for MSMEs Using RAG",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files and Templates
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"
static_dir.mkdir(parents=True, exist_ok=True)
templates_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Pydantic Request Models
class CopilotRequest(BaseModel):
    customer_id: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: Optional[int] = 100
    user_notes: Optional[str] = None
    natural_language_query: Optional[str] = None

class WhatIfSimRequest(BaseModel):
    product_sku: str
    customer_tier: str
    quantity: int
    supplier_cost: float
    discount_pct: float
    target_margin_pct: float

class CreateQuoteRequest(BaseModel):
    customer_id: str
    product_sku: str
    quantity: int
    final_quoted_price: float
    status: str = "Approved"  # Approved, Overridden, Rejected
    override_reason: Optional[str] = None
    override_notes: Optional[str] = None
    confidence_score: Optional[int] = 90
    citations: Optional[list] = []
    warnings: Optional[list] = []
    copilot_explanation: Optional[str] = ""

class UpdateStatusRequest(BaseModel):
    status: str
    override_price: Optional[float] = None
    override_reason: Optional[str] = None
    won_lost_outcome: Optional[str] = None
    outcome_notes: Optional[str] = None

# --- API ROUTES ---

@app.get("/api/info")
def get_project_info():
    return PROJECT_INFO

@app.get("/api/products")
def get_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY category, name")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/customers")
def get_customers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY tier, name")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/suppliers")
def get_suppliers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers ORDER BY reliability_rating DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.post("/api/copilot/recommend")
def copilot_recommend(req: CopilotRequest):
    # Handle natural language requests if provided
    if req.natural_language_query:
        parsed = copilot.parse_natural_language_request(req.natural_language_query)
        customer_id = parsed["customer_id"]
        product_sku = parsed["product_sku"]
        quantity = parsed["quantity"]
    else:
        customer_id = req.customer_id or "CUST-001"
        product_sku = req.product_sku or "HTB-M12-50"
        quantity = req.quantity or 100

    recommendation = copilot.generate_recommendation(
        customer_id=customer_id,
        product_sku=product_sku,
        quantity=quantity,
        user_notes=req.user_notes
    )
    return recommendation

@app.post("/api/copilot/simulate")
def simulate_what_if(req: WhatIfSimRequest):
    """
    Feature 2: What-If Pricing Simulator.
    Computes instant price, margin, profit, and floor compliance
    as user dynamically adjusts quantity, cost, discount, and target margin.
    """
    cost = float(req.supplier_cost)
    floor_margin = 9.0  # 9% floor rule
    price_floor = round(cost * (1 + (floor_margin / 100.0)), 2)

    # Base price from target margin: Markup on cost
    base_price = round(cost * (1 + (req.target_margin_pct / 100.0)), 2)

    # Apply discount
    discount_amount = round(base_price * (req.discount_pct / 100.0), 2)
    simulated_price = round(base_price - discount_amount, 2)

    # Check price floor compliance
    is_floor_compliant = simulated_price >= price_floor
    floor_deficit = round(price_floor - simulated_price, 2) if not is_floor_compliant else 0.0

    # Margins and totals
    profit_per_unit = round(simulated_price - cost, 2)
    margin_pct = round((profit_per_unit / max(0.01, simulated_price)) * 100.0, 2)
    markup_pct = round((profit_per_unit / max(0.01, cost)) * 100.0, 2)

    total_revenue = round(simulated_price * req.quantity, 2)
    total_cost = round(cost * req.quantity, 2)
    total_profit = round(total_revenue - total_cost, 2)

    return {
        "product_sku": req.product_sku,
        "quantity": req.quantity,
        "supplier_cost": cost,
        "price_floor": price_floor,
        "base_price": base_price,
        "discount_pct": req.discount_pct,
        "simulated_price": simulated_price,
        "profit_per_unit": profit_per_unit,
        "margin_pct": margin_pct,
        "markup_pct": markup_pct,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "is_floor_compliant": is_floor_compliant,
        "floor_deficit": floor_deficit,
        "warning": None if is_floor_compliant else f"FLOOR BREACH: Selling price ₹{simulated_price:.2f} is ₹{floor_deficit:.2f} below mandatory floor of ₹{price_floor:.2f}!"
    }

@app.post("/api/quotations/create")
def create_quotation(req: CreateQuoteRequest):
    # Calculate constraints to save accurate baseline & floor
    constraints = pricing_engine.calculate_constraints(req.product_sku, req.customer_id, req.quantity)
    
    # Check floor validation if price is overridden
    if req.status == "Overridden":
        valid, msg, floor = pricing_engine.validate_override(req.product_sku, req.final_quoted_price)
        if not valid and not req.override_reason:
            raise HTTPException(status_code=400, detail=msg)

    quote_id = f"Q-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    quote_number = f"APX-Q-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"

    profit_per_unit = req.final_quoted_price - constraints["effective_unit_cost"]
    margin_pct = round((profit_per_unit / max(0.01, req.final_quoted_price)) * 100.0, 2)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO quotations (
        quote_id, quote_number, customer_id, product_sku, quantity, requested_date,
        baseline_cost, price_floor, recommended_price, final_quoted_price, margin_pct,
        status, override_reason, override_notes, won_lost_outcome, outcome_notes,
        citations_json, warnings_json, confidence_score, copilot_explanation, created_at, approved_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        quote_id, quote_number, req.customer_id, req.product_sku, req.quantity,
        datetime.now().strftime("%Y-%m-%d"), constraints["effective_unit_cost"],
        constraints["price_floor"], constraints["recommended_price"], req.final_quoted_price,
        margin_pct, req.status, req.override_reason, req.override_notes, "Pending",
        None, json.dumps(req.citations), json.dumps(req.warnings), req.confidence_score,
        req.copilot_explanation, datetime.now().isoformat(),
        datetime.now().isoformat() if req.status in ("Approved", "Overridden") else None
    ))

    # Audit log
    log_audit(quote_id, f"Quotation {req.status}", "Sales Executive", {
        "final_quoted_price": req.final_quoted_price,
        "recommended_price": constraints["recommended_price"],
        "override_reason": req.override_reason
    })

    conn.commit()
    conn.close()

    return {
        "quote_id": quote_id,
        "quote_number": quote_number,
        "status": req.status,
        "final_quoted_price": req.final_quoted_price,
        "margin_pct": margin_pct,
        "message": "Quotation successfully recorded."
    }

@app.get("/api/quotations")
def list_quotations():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT q.*, c.name as customer_name, c.tier as customer_tier, p.name as product_name, p.uom as unit_of_measure, p.hsn_code
    FROM quotations q
    JOIN customers c ON q.customer_id = c.customer_id
    JOIN products p ON q.product_sku = p.sku
    ORDER BY q.created_at DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/quotations/{quote_id}")
def get_quotation_details(quote_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT q.*, c.name as customer_name, c.tier as customer_tier, c.credit_terms, p.name as product_name, p.uom as unit_of_measure, p.hsn_code
    FROM quotations q
    JOIN customers c ON q.customer_id = c.customer_id
    JOIN products p ON q.product_sku = p.sku
    WHERE q.quote_id = ?
    """, (quote_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Quotation not found")
    d = dict(row)
    if d.get("citations_json"):
        try:
            d["citations"] = json.loads(d["citations_json"])
        except Exception:
            d["citations"] = []
    if d.get("warnings_json"):
        try:
            d["warnings"] = json.loads(d["warnings_json"])
        except Exception:
            d["warnings"] = []
    return d

@app.get("/api/quotations/{quote_id}/pdf")
def download_quotation_pdf(quote_id: str):
    quote_data = get_quotation_details(quote_id)
    pdf_buffer = generate_quotation_pdf(quote_data)
    filename = f"Quotation_{quote_data.get('quote_number', quote_id)}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/api/quotations/{quote_id}/update_status")
def update_quote_status(quote_id: str, req: UpdateStatusRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quotations WHERE quote_id = ?", (quote_id,))
    quote = cursor.fetchone()
    if not quote:
        conn.close()
        raise HTTPException(status_code=404, detail="Quotation not found")

    quote = dict(quote)

    if req.override_price is not None:
        valid, msg, floor = pricing_engine.validate_override(quote["product_sku"], req.override_price)
        if not valid and not req.override_reason:
            conn.close()
            raise HTTPException(status_code=400, detail=msg)
        
        profit_per_unit = req.override_price - quote["baseline_cost"]
        new_margin = round((profit_per_unit / max(0.01, req.override_price)) * 100.0, 2)
        cursor.execute("""
        UPDATE quotations SET status = ?, final_quoted_price = ?, margin_pct = ?, override_reason = ?, approved_at = ?
        WHERE quote_id = ?
        """, (req.status, req.override_price, new_margin, req.override_reason, datetime.now().isoformat(), quote_id))
    else:
        cursor.execute("""
        UPDATE quotations SET status = ?, approved_at = ? WHERE quote_id = ?
        """, (req.status, datetime.now().isoformat(), quote_id))

    if req.won_lost_outcome:
        cursor.execute("""
        UPDATE quotations SET won_lost_outcome = ?, outcome_notes = ? WHERE quote_id = ?
        """, (req.won_lost_outcome, req.outcome_notes, quote_id))

    conn.commit()
    conn.close()

    return {"message": f"Quotation {quote_id} status updated to {req.status}."}

@app.get("/api/documents")
def list_documents():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM document_metadata ORDER BY date_issued DESC")
    docs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return docs

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    doc_type: Optional[str] = Form(None)
):
    """
    Feature 3: Document Ingestion, Stale-Data and Conflict Detection.
    """
    file_bytes = await file.read()
    result = ingestion_service.ingest_document(
        filename=file.filename,
        file_bytes=file_bytes,
        title=title,
        custom_doc_type=doc_type
    )
    return result

@app.get("/api/audit/run")
def run_quotation_audit(product_sku: str = "HTB-M12-50", customer_id: str = "CUST-001", quantity: int = 500):
    """
    Feature 4: Genuinely Impressive AI Quotation Auditor.
    """
    audit_report = ingestion_service.run_ai_quotation_audit(product_sku, customer_id, quantity)
    return audit_report

@app.get("/api/analytics")
def get_analytics():
    """
    Feature 4: Learning from Past Quotations & Win/Loss Analytics.
    """
    return analytics_service.get_win_loss_analytics()

@app.get("/api/evaluate")
def run_evaluation():
    """
    Section 8 of Synopsis: Baseline vs PricePilot AI Experimental Comparison.
    """
    return evaluation_service.run_benchmark_experiments()

@app.get("/api/settings")
def get_settings():
    return DEFAULT_SETTINGS

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"project": PROJECT_INFO})
