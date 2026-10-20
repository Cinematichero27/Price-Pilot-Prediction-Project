import json
from datetime import datetime
from backend.database import get_connection, init_db

def seed_database():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Seed Products
    products = [
        ("HTB-M12-50", "High-Tensile Hex Bolt Grade 8.8 (M12 x 50mm)", "Fasteners", 18.40, 4200, 1000, "PCS", 3, 24.0, "73181500", "Cold forged alloy steel bolt conforming to IS:1367 / ISO 898-1 with black oxide coating."),
        ("SSC-M8-30", "Stainless Steel Socket Cap Screw SS316 (M8 x 30mm)", "Fasteners", 28.70, 1800, 800, "PCS", 5, 26.0, "73181500", "Austenitic marine-grade stainless steel cap screw with precision Allen drive."),
        ("HFN-M16-10", "Heavy Hex Flange Nut Grade 10 (M16)", "Nuts & Washers", 29.50, 1500, 1200, "PCS", 4, 22.0, "73181600", "High strength flange nut with serrated locking bearing surface."),
        ("STR-B7-1M", "Industrial Threaded Stud Rod B7 (1m x 20mm)", "Rods & Studs", 340.00, 350, 150, "PCS", 7, 25.0, "73181900", "ASTM A193 Grade B7 heat-treated chrome-moly steel stud rod for high-pressure flanges."),
        ("BI-M4-15", "Precision Brass Inserts & Hex Standoffs (M4 x 15mm)", "Precision Parts", 12.40, 8500, 2000, "PCS", 2, 30.0, "74153300", "RoHS compliant free-cutting brass knurled insert with 5-8 microns nickel plating."),
        ("GSW-M14", "Galvanized Spring Washers Heavy Duty (M14)", "Nuts & Washers", 4.80, 15000, 5000, "PCS", 2, 28.0, "73182100", "Electro-galvanized spring steel split washer conforming to DIN 127B.")
    ]
    cursor.executemany("""
    INSERT OR REPLACE INTO products (sku, name, category, unit_cost, current_stock, reorder_level, uom, default_lead_time_days, base_margin_pct, hsn_code, description)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, products)

    # 2. Seed Customers
    customers = [
        ("CUST-001", "Bharat Heavy Machinery Corp.", "Heavy Engineering & Defense", "Platinum", "Net 45", 7500000.0, "Moderate", "Annual Master Supply Agreement (MSA-2026-BHMC). Strategic partner entitled to 5% baseline partner rebate stackable with volume discount."),
        ("CUST-002", "Precision Auto Ancillaries Ltd.", "Automotive Tier 1", "Gold", "Net 30", 3800000.0, "Moderate", "High frequency orders, requires PPAP Level 3 documentation and zero defect packaging."),
        ("CUST-003", "Deccan Fabrication Works", "Structural & Fabrication", "Silver", "Net 15", 1450000.0, "High", "Extremely price-sensitive. Lost previous August tender to Sundaram distributor. Requires pricing between ₹34.80 - ₹35.40 on M16 Flange Nuts to recapture account."),
        ("CUST-004", "Apex Agro Equipments", "Agricultural Machinery", "Bronze", "Advance / 7-Day", 620000.0, "Moderate", "Spot purchaser, seasonal ordering peaks in Q1 and Q3. Standard terms apply."),
        ("CUST-005", "Zenith Electricals & Switchgears", "Electrical & Switchgear", "Gold", "Net 30", 2200000.0, "Low", "Quality-focused buyer. Requires 100% RoHS compliance and NABL batch test certificates. Accepts premium pricing up to ₹18.50 for brass inserts.")
    ]
    cursor.executemany("""
    INSERT OR REPLACE INTO customers (customer_id, name, industry, tier, credit_terms, lifetime_volume, price_sensitivity, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, customers)

    # 3. Seed Suppliers
    suppliers = [
        ("SUPP-001", "Tata Special Steels Ltd.", "Alloy & Carbon Steel Wire Rods", 4.9, 12, "sales.west@tatasteels.com"),
        ("SUPP-002", "Jindal Stainless Wire Industries", "Stainless Steel Wire & Coils", 4.7, 15, "industrial@jindalstainless.com"),
        ("SUPP-003", "MicroCoat Zinc & Galvanizing Works", "Electroplating & Surface Treatment", 3.8, 4, "orders@microcoat.co.in"),
        ("SUPP-004", "SuperHeat Thermal Solutions", "Vacuum Hardening & Heat Treatment", 4.5, 5, "contact@superheat.in")
    ]
    cursor.executemany("""
    INSERT OR REPLACE INTO suppliers (supplier_id, name, material_category, reliability_rating, lead_time_days, contact)
    VALUES (?, ?, ?, ?, ?, ?)
    """, suppliers)

    # 4. Seed Pricing Rules
    rules = [
        ("RULE-01", "Mandatory Floor Margin Rule", "floor_constraint", json.dumps({"min_margin_pct": 9.0, "enforce_hard_block": True}), 1),
        ("RULE-02", "Customer Tier Margin Matrix", "tier_margin", json.dumps({
            "Platinum": {"min_margin": 14.0, "target_margin": 16.0},
            "Gold": {"min_margin": 18.0, "target_margin": 20.0},
            "Silver": {"min_margin": 22.0, "target_margin": 24.0},
            "Bronze": {"min_margin": 26.0, "target_margin": 28.0}
        }), 1),
        ("RULE-03", "Standard Volume Discount Tiers", "volume_discount", json.dumps({
            "tiers": [
                {"min_qty": 1, "max_qty": 99, "discount_pct": 0.0},
                {"min_qty": 100, "max_qty": 499, "discount_pct": 3.5},
                {"min_qty": 500, "max_qty": 999, "discount_pct": 6.0},
                {"min_qty": 1000, "max_qty": 4999, "discount_pct": 9.0},
                {"min_qty": 5000, "max_qty": 999999, "discount_pct": 12.0}
            ]
        }), 1),
        ("RULE-04", "Inventory Balance Incentive & Surcharge", "inventory_rule", json.dumps({
            "stockout_surcharge_pct": 3.0,
            "excess_stock_clearance_discount_pct": 2.0
        }), 1)
    ]
    cursor.executemany("""
    INSERT OR REPLACE INTO pricing_rules (rule_id, rule_name, rule_type, parameters_json, is_active)
    VALUES (?, ?, ?, ?, ?)
    """, rules)

    # 5. Seed Document Metadata
    docs_metadata = [
        ("DOC-01", "doc_01_pricing_policy_q4_2026.txt", "Corporate Pricing & Margin Policy - Q4 FY2026", "Pricing Policy", "2026-10-01", "2026-10-01", "2026-12-31", 1, 0, None, "Mandatory floor price rule (Cost + 9%), standard customer tier margins, and volume discount schedule.", 3, "2026-10-01T09:00:00"),
        ("DOC-02", "doc_02_supplier_tata_steel_oct2026.txt", "Tata Steel Wire Rod Price Revision & Surcharge Notice", "Supplier Quotation", "2026-10-01", "2026-10-05", "2026-12-31", 1, 0, None, "Active notice raising Grade 8.8 wire rod from ₹62.50 to ₹66.30/kg. Hex Bolt M12x50 direct cost revised to ₹18.40.", 2, "2026-10-01T10:30:00"),
        ("DOC-03", "doc_03_supplier_tata_steel_may2026_superseded.txt", "Tata Steel Raw Material Quotation - Q2 FY2026 (SUPERSEDED)", "Supplier Quotation", "2026-05-15", "2026-05-15", "2026-09-30", 0, 0, "DOC-02", "Outdated Q2 quote stating ₹16.75 unit cost. Expired on 2026-09-30, superseded by DOC-02.", 2, "2026-05-15T11:00:00"),
        ("DOC-04", "doc_04_supplier_jindal_stainless_aug2026.txt", "Jindal Stainless SS316 Specification & Supply Contract", "Supplier Quotation", "2026-08-10", "2026-08-15", "2026-11-30", 1, 0, None, "Active supply contract establishing SS316 socket cap screw unit cost at ₹28.70.", 2, "2026-08-10T14:15:00"),
        ("DOC-05", "doc_05_customer_msa_bharat_heavy.txt", "Master Supply Agreement - Bharat Heavy Machinery Corp.", "Customer Agreement", "2026-01-15", "2026-01-15", "2026-12-31", 1, 0, None, "Platinum tier agreement granting 5% partner discount stackable up to 12% max discount with Net-45 credit.", 3, "2026-01-15T16:00:00"),
        ("DOC-06", "doc_06_negotiation_notes_deccan_fab.txt", "Win/Loss Debrief & Competitive Analysis - Deccan Fabrication", "Negotiation Note", "2026-09-12", "2026-09-12", "2026-12-31", 1, 0, None, "Lost tender debrief: Deccan requires ₹34.80-₹35.40 on M16 Flange Nuts (15-17% margin) with NABL certificate to win back order.", 2, "2026-09-12T17:30:00"),
        ("DOC-07", "doc_07_negotiation_notes_zenith.txt", "Key Account Requirements - Zenith Electricals", "Negotiation Note", "2026-07-20", "2026-07-20", "2027-03-31", 1, 0, None, "Zenith requires RoHS and 5-8 micron plating; price inelastic up to ₹18.50 for brass inserts with inspection certificates.", 2, "2026-07-20T10:00:00"),
        ("DOC-08", "doc_08_supplier_microcoat_zinc_conflicting.txt", "MicroCoat Surface Treatment Circular & Email Conflict", "Supplier Quotation", "2026-09-25", "2026-09-25", "2026-12-31", 1, 1, None, "Conflicting guidelines: Formal circular requires ₹1.40/kg surcharge under 500kg, but email waived fee for orders > ₹40,000.", 2, "2026-09-25T15:20:00")
    ]
    cursor.executemany("""
    INSERT OR REPLACE INTO document_metadata (doc_id, filename, title, doc_type, date_issued, effective_date, valid_until, is_active, is_conflicting, superseded_by_id, summary, chunk_count, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, docs_metadata)

    # 6. Seed Realistic Historical Quotations
    historical_quotes = [
        ("Q-2026-0812", "APX-Q-2026-0812", "CUST-001", "HTB-M12-50", 1000, "2026-09-15", 16.75, 18.26, 20.40, 20.40, 17.89, "Approved", None, None, "Won", "Customer accepted Q3 price before steel surcharge.", json.dumps(["DOC-05", "DOC-01"]), json.dumps([]), 92, "Standard Platinum tier pricing with MSA 5% partner discount applied.", "2026-09-15T11:20:00", "2026-09-15T11:45:00"),
        ("Q-2026-0834", "APX-Q-2026-0834", "CUST-003", "HFN-M16-10", 1000, "2026-08-20", 29.50, 32.16, 36.80, 36.80, 19.84, "Approved", None, None, "Lost", "Lost to Sundaram distributor who quoted ₹34.20. Sales did not discount.", json.dumps(["DOC-01"]), json.dumps(["Price sensitivity risk"]), 78, "Standard Silver tier pricing applied without competitive adjustment.", "2026-08-20T14:10:00", "2026-08-20T14:30:00"),
        ("Q-2026-0890", "APX-Q-2026-0890", "CUST-005", "BI-M4-15", 2000, "2026-06-18", 12.40, 13.52, 17.90, 17.90, 30.73, "Approved", None, None, "Won", "Zenith accepted with RoHS test certs.", json.dumps(["DOC-07"]), json.dumps([]), 95, "Account-specific quality-first pricing applied.", "2026-06-18T10:00:00", "2026-06-18T10:15:00"),
        ("Q-2026-0905", "APX-Q-2026-0905", "CUST-002", "SSC-M8-30", 500, "2026-09-28", 28.70, 31.28, 34.20, 33.50, 14.33, "Overridden", "Matched authorized distributor price for automotive tier 1 client", "Approved by Sales Director", "Won", "Order secured against local rival.", json.dumps(["DOC-04", "DOC-01"]), json.dumps(["Customer tier negotiation"]), 88, "Gold tier base price adjusted for volume bracket.", "2026-09-28T16:20:00", "2026-09-28T16:50:00")
    ]
    cursor.executemany("""
    INSERT OR REPLACE INTO quotations (quote_id, quote_number, customer_id, product_sku, quantity, requested_date, baseline_cost, price_floor, recommended_price, final_quoted_price, margin_pct, status, override_reason, override_notes, won_lost_outcome, outcome_notes, citations_json, warnings_json, confidence_score, copilot_explanation, created_at, approved_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, historical_quotes)

    conn.commit()
    conn.close()
    print("Database successfully seeded with realistic B2B MSME pricing dataset.")

if __name__ == "__main__":
    seed_database()
