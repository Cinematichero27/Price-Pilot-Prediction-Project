from typing import Dict, Any, Tuple
import json
from backend.database import get_connection

class DeterministicPricingEngine:
    """
    Deterministic Financial & Constraint Pricing Engine.
    KEY ARCHITECTURAL PRINCIPLE:
    The LLM is NOT the source of truth for numerical calculations.
    This engine strictly computes unit costs, hard floor constraints,
    customer tier margins, volume breaks, and valid pricing boundaries.
    """

    def __init__(self):
        self.floor_margin_pct = 9.0  # Mandatory 9% floor margin to prevent losses

    def calculate_constraints(
        self,
        product_sku: str,
        customer_id: str,
        quantity: int,
        context_modifiers: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calculates all hard constraints and deterministic pricing parameters.
        """
        conn = get_connection()
        cursor = conn.cursor()

        # Fetch product details
        cursor.execute("SELECT * FROM products WHERE sku = ?", (product_sku,))
        product = cursor.fetchone()
        if not product:
            conn.close()
            raise ValueError(f"Product SKU '{product_sku}' not found.")
        product = dict(product)

        # Fetch customer details
        cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            conn.close()
            raise ValueError(f"Customer ID '{customer_id}' not found.")
        customer = dict(customer)

        # Fetch pricing rules
        cursor.execute("SELECT * FROM pricing_rules WHERE is_active = 1")
        rules_rows = cursor.fetchall()
        rules = {r["rule_type"]: json.loads(r["parameters_json"]) for r in rules_rows}

        conn.close()

        # 1. Base Cost Calculation
        unit_cost = float(product["unit_cost"])

        # Check if RAG context provided a recent raw material surcharge or adjustment
        cost_adjustment = 0.0
        if context_modifiers and "cost_adjustment" in context_modifiers:
            cost_adjustment = float(context_modifiers["cost_adjustment"])
        effective_unit_cost = round(unit_cost + cost_adjustment, 2)

        # 2. Hard Price Floor (Mandatory Loss Prevention)
        floor_margin_rule = rules.get("floor_constraint", {}).get("min_margin_pct", self.floor_margin_pct)
        # Price Floor = Cost / (1 - margin) or Cost * (1 + margin)
        # In Indian MSME manufacturing standard, Margin on Cost (Markup):
        price_floor = round(effective_unit_cost * (1 + (floor_margin_rule / 100.0)), 2)

        # 3. Customer Tier Target Margin
        tier = customer.get("tier", "Bronze")
        tier_rule = rules.get("tier_margin", {}).get(tier, {"min_margin": 24.0, "target_margin": 26.0})
        tier_target_margin_pct = float(tier_rule["target_margin"])
        tier_min_margin_pct = float(tier_rule["min_margin"])

        # Standard list price based on tier target margin
        standard_tier_price = round(effective_unit_cost * (1 + (tier_target_margin_pct / 100.0)), 2)

        # 4. Volume Discount Bracket
        volume_rules = rules.get("volume_discount", {}).get("tiers", [])
        volume_discount_pct = 0.0
        for bracket in volume_rules:
            if bracket["min_qty"] <= quantity <= bracket["max_qty"]:
                volume_discount_pct = float(bracket["discount_pct"])
                break

        # Check for Strategic Customer MSA Rebate
        msa_discount_pct = 0.0
        if context_modifiers and "msa_partner_discount_pct" in context_modifiers:
            msa_discount_pct = float(context_modifiers["msa_partner_discount_pct"])

        total_discount_pct = min(12.0, volume_discount_pct + msa_discount_pct)  # Capped at 12% max combined discount

        # Apply volume discount
        discounted_unit_price = round(standard_tier_price * (1 - (total_discount_pct / 100.0)), 2)

        # 5. Inventory and Lead Time Constraint Check
        current_stock = int(product["current_stock"])
        reorder_level = int(product["reorder_level"])
        inventory_status = "Adequate"
        inventory_price_delta = 0.0

        if quantity > current_stock:
            inventory_status = "Stockout Risk (Procurement/Production Needed)"
            # Expedited fee 2.5% if lead time is tight
            expedited_pct = rules.get("inventory_rule", {}).get("stockout_surcharge_pct", 3.0)
            inventory_price_delta = round(effective_unit_cost * (expedited_pct / 100.0), 2)
        elif current_stock > (reorder_level * 2.5):
            inventory_status = "Surplus Stock (Liquidation Incentive Allowed)"
            clearance_pct = rules.get("inventory_rule", {}).get("excess_stock_clearance_discount_pct", 2.0)
            inventory_price_delta = -round(effective_unit_cost * (clearance_pct / 100.0), 2)

        # 6. Recommended Price Calculation
        target_price = round(discounted_unit_price + inventory_price_delta, 2)

        # Apply specific competitive context modifier if present (e.g. Deccan Fab win-back recommendation)
        if context_modifiers and "target_price_cap" in context_modifiers:
            capped_price = float(context_modifiers["target_price_cap"])
            if capped_price >= price_floor:
                target_price = min(target_price, capped_price)

        # Ensure recommendation NEVER breaches price floor!
        recommended_price = max(price_floor, target_price)

        # Define valid negotiation corridor [min_acceptable, target, max_list]
        recommended_range_min = max(price_floor, round(recommended_price * 0.97, 2))
        recommended_range_max = round(max(recommended_price * 1.04, standard_tier_price), 2)

        # Calculate achieved margin percentage: ((Price - Cost) / Price) * 100
        gross_profit_per_unit = recommended_price - effective_unit_cost
        margin_pct = round((gross_profit_per_unit / recommended_price) * 100.0, 2)
        markup_pct = round((gross_profit_per_unit / effective_unit_cost) * 100.0, 2)

        total_amount = round(recommended_price * quantity, 2)
        total_cost = round(effective_unit_cost * quantity, 2)
        total_profit = round(total_amount - total_cost, 2)

        return {
            "product_sku": product["sku"],
            "product_name": product["name"],
            "customer_id": customer["customer_id"],
            "customer_name": customer["name"],
            "customer_tier": tier,
            "quantity": quantity,
            "unit_of_measure": product["uom"],
            "base_unit_cost": unit_cost,
            "cost_adjustment": cost_adjustment,
            "effective_unit_cost": effective_unit_cost,
            "price_floor": price_floor,
            "standard_list_price": standard_tier_price,
            "volume_discount_pct": volume_discount_pct,
            "msa_discount_pct": msa_discount_pct,
            "total_discount_pct": total_discount_pct,
            "inventory_status": inventory_status,
            "inventory_adjustment": inventory_price_delta,
            "recommended_price": recommended_price,
            "recommended_range_min": recommended_range_min,
            "recommended_range_max": recommended_range_max,
            "gross_profit_per_unit": round(gross_profit_per_unit, 2),
            "margin_pct": margin_pct,
            "markup_pct": markup_pct,
            "total_amount": total_amount,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "current_stock": current_stock,
            "hsn_code": product["hsn_code"]
        }

    def validate_override(self, product_sku: str, override_price: float) -> Tuple[bool, str, float]:
        """
        Validates whether a human sales rep override is acceptable or breaches the price floor.
        Returns: (is_valid, message, price_floor)
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT unit_cost FROM products WHERE sku = ?", (product_sku,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False, f"Product SKU {product_sku} not found", 0.0

        unit_cost = float(row["unit_cost"])
        price_floor = round(unit_cost * (1 + (self.floor_margin_pct / 100.0)), 2)

        if override_price < price_floor:
            breach_amount = round(price_floor - override_price, 2)
            return False, f"CRITICAL CONSTRAINT VIOLATION: Quoted price ₹{override_price:.2f} is below the mandatory Price Floor of ₹{price_floor:.2f} (Direct Cost ₹{unit_cost:.2f} + 9% floor margin). Deficit: ₹{breach_amount:.2f}/unit.", price_floor
        
        return True, f"Valid override. Price ₹{override_price:.2f} satisfies the floor constraint of ₹{price_floor:.2f}.", price_floor

pricing_engine = DeterministicPricingEngine()
