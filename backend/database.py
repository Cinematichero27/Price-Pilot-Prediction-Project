import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.config import DB_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_cost REAL NOT NULL,
        current_stock INTEGER NOT NULL,
        reorder_level INTEGER NOT NULL,
        uom TEXT NOT NULL,
        default_lead_time_days INTEGER NOT NULL,
        base_margin_pct REAL NOT NULL,
        hsn_code TEXT NOT NULL,
        description TEXT
    )
    """)

    # Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        industry TEXT NOT NULL,
        tier TEXT NOT NULL,
        credit_terms TEXT NOT NULL,
        lifetime_volume REAL NOT NULL DEFAULT 0.0,
        price_sensitivity TEXT NOT NULL,
        notes TEXT
    )
    """)

    # Suppliers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        material_category TEXT NOT NULL,
        reliability_rating REAL NOT NULL,
        lead_time_days INTEGER NOT NULL,
        contact TEXT
    )
    """)

    # Pricing Rules Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pricing_rules (
        rule_id TEXT PRIMARY KEY,
        rule_name TEXT NOT NULL,
        rule_type TEXT NOT NULL,
        parameters_json TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """)

    # Quotations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quotations (
        quote_id TEXT PRIMARY KEY,
        quote_number TEXT NOT NULL UNIQUE,
        customer_id TEXT NOT NULL,
        product_sku TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        requested_date TEXT NOT NULL,
        baseline_cost REAL NOT NULL,
        price_floor REAL NOT NULL,
        recommended_price REAL NOT NULL,
        final_quoted_price REAL NOT NULL,
        margin_pct REAL NOT NULL,
        status TEXT NOT NULL, -- Draft, Recommended, Approved, Overridden, Rejected
        override_reason TEXT,
        override_notes TEXT,
        won_lost_outcome TEXT, -- Won, Lost, Pending
        outcome_notes TEXT,
        citations_json TEXT,
        warnings_json TEXT,
        confidence_score INTEGER,
        copilot_explanation TEXT,
        created_at TEXT NOT NULL,
        approved_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (product_sku) REFERENCES products(sku)
    )
    """)

    # Document Metadata & Tracking Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_metadata (
        doc_id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        title TEXT NOT NULL,
        doc_type TEXT NOT NULL, -- Policy, Supplier Quotation, Customer Agreement, Negotiation Note
        date_issued TEXT NOT NULL,
        effective_date TEXT NOT NULL,
        valid_until TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        is_conflicting INTEGER NOT NULL DEFAULT 0,
        superseded_by_id TEXT,
        summary TEXT,
        chunk_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)

    # Audit / Overrides Log Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_id TEXT NOT NULL,
        action TEXT NOT NULL,
        actor TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def log_audit(quote_id: str, action: str, actor: str, details: Dict[str, Any]):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (quote_id, action, actor, details, timestamp) VALUES (?, ?, ?, ?, ?)",
        (quote_id, action, actor, json.dumps(details), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
