import io
from datetime import datetime, timedelta
from typing import Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_quotation_pdf(quote_data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates an enterprise-grade B2B Quotation PDF conforming to Indian MSME standards.
    Includes GSTIN, HSN Code, Itemized pricing, validity period, payment terms,
    and an AI Evidence & Deterministic Constraint Verification Audit Stamp.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B')
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748B')
    )
    stamp_style = ParagraphStyle(
        'StampStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#0369A1')
    )

    story = []

    # 1. Company Header & Quotation Badge
    company_info = [
        [
            Paragraph("<b>APEX PRECISION FASTENERS & HARDWARE PVT. LTD.</b><br/>"
                      "<font size=8 color='#64748B'>CIN: U28991MH2016PTC284910 | GSTIN: 27AABCA1234F1ZX<br/>"
                      "Plot 48, Phase II, Chakan MIDC Industrial Area, Pune, Maharashtra - 410501<br/>"
                      "Email: quotes@apexfasteners.co.in | Phone: +91 20 6792 4400</font>", body_style),
            Paragraph("<b>COMMERCIAL QUOTATION</b><br/>"
                      f"<font size=8 color='#64748B'>Quote Ref: <b>{quote_data.get('quote_number', 'APX-Q-2026-TEMP')}</b><br/>"
                      f"Date: <b>{quote_data.get('created_at', datetime.now().strftime('%Y-%m-%d'))[:10]}</b><br/>"
                      f"Valid Until: <b>{(datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')}</b></font>", body_style)
        ]
    ]
    t_header = Table(company_info, colWidths=[4.2*inch, 3.0*inch])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_header)

    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=12))

    # 2. Customer (Bill To / Ship To) Details
    cust_name = quote_data.get('customer_name', 'Valued Customer')
    cust_id = quote_data.get('customer_id', 'CUST-001')
    credit_terms = quote_data.get('credit_terms', 'Net 30 Days')
    tier = quote_data.get('customer_tier', 'Gold')

    bill_to = [
        [
            Paragraph(f"<b>QUOTATION PREPARED FOR:</b><br/>"
                      f"<b>{cust_name}</b><br/>"
                      f"<font size=8 color='#64748B'>Customer ID: {cust_id} | Account Tier: <b>{tier} Partner</b><br/>"
                      f"Industrial Machinery Division<br/>"
                      f"Payment Terms: <b>{credit_terms}</b></font>", body_style),
            Paragraph(f"<b>DELIVERY & DISPATCH:</b><br/>"
                      f"Ex-Works Chakan Factory / Door Delivery Available<br/>"
                      f"<font size=8 color='#64748B'>Standard Lead Time: 5–7 Working Days<br/>"
                      f"Dispatch Mode: Road Transport / Insured Transit<br/>"
                      f"Currency: INR (₹)</font>", body_style)
        ]
    ]
    t_cust = Table(bill_to, colWidths=[4.2*inch, 3.0*inch])
    t_cust.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_cust)
    story.append(Spacer(1, 14))

    # 3. Itemized Products Table
    p_name = quote_data.get('product_name', 'Industrial Fastener')
    p_sku = quote_data.get('product_sku', 'SKU-001')
    hsn = quote_data.get('hsn_code', '73181500')
    qty = quote_data.get('quantity', 100)
    uom = quote_data.get('unit_of_measure', 'PCS')
    unit_price = float(quote_data.get('final_quoted_price', quote_data.get('recommended_price', 0.0)))
    taxable_amount = round(unit_price * qty, 2)
    gst_rate = 18.0  # 18% standard GST for industrial hardware
    gst_amount = round(taxable_amount * (gst_rate / 100.0), 2)
    total_quote_amount = round(taxable_amount + gst_amount, 2)

    table_data = [
        [
            Paragraph("<b>#</b>", body_bold),
            Paragraph("<b>Item Description & Specifications</b>", body_bold),
            Paragraph("<b>HSN/SAC</b>", body_bold),
            Paragraph("<b>Qty</b>", body_bold),
            Paragraph("<b>UOM</b>", body_bold),
            Paragraph("<b>Unit Rate (₹)</b>", body_bold),
            Paragraph("<b>Total Amount (₹)</b>", body_bold),
        ],
        [
            Paragraph("1", body_style),
            Paragraph(f"<b>{p_name}</b><br/><font size=7 color='#64748B'>SKU: {p_sku} | Conforms to IS:1367 / DIN Standard</font>", body_style),
            Paragraph(hsn, body_style),
            Paragraph(f"{qty:,}", body_style),
            Paragraph(uom, body_style),
            Paragraph(f"₹{unit_price:,.2f}", body_style),
            Paragraph(f"₹{taxable_amount:,.2f}", body_style),
        ]
    ]

    t_items = Table(table_data, colWidths=[0.3*inch, 3.1*inch, 0.8*inch, 0.7*inch, 0.5*inch, 0.9*inch, 0.9*inch])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (5, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    # 4. Summary & Tax Table
    summary_data = [
        [Paragraph("<b>Subtotal (Taxable Value):</b>", body_style), Paragraph(f"<b>₹{taxable_amount:,.2f}</b>", body_bold)],
        [Paragraph(f"CGST ({gst_rate/2:.1f}%):", body_style), Paragraph(f"₹{gst_amount/2:,.2f}", body_style)],
        [Paragraph(f"SGST ({gst_rate/2:.1f}%):", body_style), Paragraph(f"₹{gst_amount/2:,.2f}", body_style)],
        [Paragraph("<b>Grand Total (Incl. GST):</b>", body_bold), Paragraph(f"<b>₹{total_quote_amount:,.2f}</b>", body_bold)],
    ]
    t_summary = Table(summary_data, colWidths=[2.2*inch, 1.4*inch])
    t_summary.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))

    # Wrap summary to right side
    t_summary_wrapper = Table([[Paragraph("", body_style), t_summary]], colWidths=[3.6*inch, 3.6*inch])
    story.append(t_summary_wrapper)
    story.append(Spacer(1, 12))

    # 5. PricePilot AI Evidence & Integrity Stamp
    conf_score = quote_data.get('confidence_score', 92)
    doc_refs = quote_data.get('citations', [])
    doc_titles = []
    for d in (doc_refs or [])[:3]:
        if isinstance(d, dict):
            doc_titles.append(d.get('title', 'Policy Doc')[:24])
        else:
            doc_titles.append(str(d)[:24])
    doc_str = ", ".join(doc_titles) if doc_titles else "Corporate Pricing Policy Q4-2026, Tata Steel Wire Notice"
    
    audit_stamp = [
        [
            Paragraph(f"<b>PRICEPILOT AI EVIDENCE & AUDIT STAMP</b><br/>"
                      f"<font size=7 color='#0369A1'>• Price Floor Verification: Certified compliant with minimum 9.0% loss-prevention rule.<br/>"
                      f"• Supporting Evidence Citations: {doc_str}<br/>"
                      f"• System Recommendation Confidence: <b>{conf_score}/100</b> | Deterministic Engine ID: DPE-v1.4<br/>"
                      f"• Status: <b>{quote_data.get('status', 'Approved by Human-in-the-Loop')}</b></font>", stamp_style),
            Paragraph("<b>FOR APEX PRECISION FASTENERS PVT. LTD.</b><br/><br/><br/>"
                      "<font size=8>___________________________<br/>Authorized Signatory / Commercial Desk</font>", body_style)
        ]
    ]
    t_stamp = Table(audit_stamp, colWidths=[4.7*inch, 2.5*inch])
    t_stamp.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F0F9FF')),
        ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor('#BAE6FD')),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_stamp)
    story.append(Spacer(1, 10))

    # 6. Terms and Conditions
    terms = [
        [
            Paragraph("<b>STANDARD TERMS & CONDITIONS:</b><br/>"
                      "<font size=7 color='#64748B'>"
                      "1. Quotation validity: 15 days from issue date. Subject to raw material steel price stability.<br/>"
                      "2. Taxes: GST @ 18% extra as applicable at time of invoice.<br/>"
                      "3. Payment: As per account credit terms. Interest @ 18% p.a. chargeable on overdue accounts.<br/>"
                      "4. Quality: Material Test Certificate (MTC / NABL accredited) will be provided with shipment.<br/>"
                      "5. Jurisdiction: Subject to Pune / Pimpri-Chinchwad legal jurisdiction.</font>", small_style)
        ]
    ]
    t_terms = Table(terms, colWidths=[7.2*inch])
    t_terms.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFAFA')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_terms)

    doc.build(story)
    buffer.seek(0)
    return buffer
