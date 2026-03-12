"""
Generates realistic sample Excel files for testing the CommercePulse++ pipeline.
Creates one file per domain for a test seller.

Usage:
    python generate_sample_data.py --output_dir ./sample_data
"""
import argparse
import os
import random
from datetime import date, timedelta

import pandas as pd

SELLER_ID    = "test-seller-001"
MARKETPLACES = ["flipkart", "amazon_in", "meesho", "myntra"]
SKUS         = [f"SKU-{i:04d}" for i in range(1, 21)]  # 20 products
TODAY        = date.today()


def random_date(days_back=30) -> str:
    delta = random.randint(0, days_back)
    return (TODAY - timedelta(days=delta)).isoformat()


def make_orders(n=200) -> pd.DataFrame:
    statuses = ["delivered", "delivered", "delivered", "cancelled", "returned"]
    rows = []
    for i in range(n):
        sku         = random.choice(SKUS)
        marketplace = random.choice(MARKETPLACES)
        qty         = random.randint(1, 3)
        sell_price  = round(random.uniform(299, 4999), 2)
        cost_price  = round(sell_price * random.uniform(0.4, 0.7), 2)
        discount    = round(sell_price * random.uniform(0, 0.15), 2)
        status      = random.choice(statuses)
        order_dt    = random_date(30)
        rows.append({
            "Order ID":           f"ORD-{i+1:06d}",
            "Marketplace":        marketplace,
            "SKU":                sku,
            "Status":             status,
            "Quantity":           qty,
            "Selling Price":      sell_price,
            "Cost Price":         cost_price,
            "Discount":           discount,
            "Tax":                round(sell_price * 0.18, 2),
            "Shipping Fee":       round(random.uniform(30, 120), 2),
            "Order Date":         order_dt,
            "Delivery Date":      (date.fromisoformat(order_dt) + timedelta(days=random.randint(2, 7))).isoformat()
                                  if status == "delivered" else "",
            "Return":             status == "returned",
            "Cancellation Reason": "Customer request" if status == "cancelled" else "",
        })
    return pd.DataFrame(rows)


def make_inventory() -> pd.DataFrame:
    rows = []
    for sku in SKUS:
        for mp in random.sample(MARKETPLACES, k=random.randint(1, 3)):
            stock = random.randint(0, 500)
            rows.append({
                "SKU":               sku,
                "Marketplace":       mp,
                "Available Stock":   stock,
                "Reserved Stock":    random.randint(0, min(stock, 20)),
                "Reorder Threshold": random.randint(10, 50),
                "Days of Stock":     round(stock / max(random.uniform(2, 20), 1), 1),
                "Warehouse":         random.choice(["BOM-WH1", "DEL-WH2", "BLR-WH3"]),
                "Snapshot Date":     TODAY.isoformat(),
            })
    return pd.DataFrame(rows)


def make_pricing() -> pd.DataFrame:
    rows = []
    for sku in SKUS:
        for mp in random.sample(MARKETPLACES, k=random.randint(1, 3)):
            sell  = round(random.uniform(299, 4999), 2)
            cost  = round(sell * random.uniform(0.35, 0.65), 2)
            mrp   = round(sell * random.uniform(1.1, 1.4), 2)
            comm  = round(sell * random.uniform(0.05, 0.18), 2)
            net_m = round(sell - cost - comm, 2)
            rows.append({
                "SKU":               sku,
                "Marketplace":       mp,
                "Selling Price":     sell,
                "Cost Price":        cost,
                "MRP":               mrp,
                "Commission %":      round((comm / sell) * 100, 2),
                "Commission Amount": comm,
                "Discount %":        round(((mrp - sell) / mrp) * 100, 2),
                "Net Margin":        net_m,
                "Margin %":          round((net_m / sell) * 100, 2),
                "Snapshot Date":     TODAY.isoformat(),
            })
    return pd.DataFrame(rows)


def make_traffic(days=14) -> pd.DataFrame:
    rows = []
    for sku in SKUS:
        for mp in random.sample(MARKETPLACES, k=2):
            for d in range(days):
                dt         = (TODAY - timedelta(days=d)).isoformat()
                impressions = random.randint(100, 10000)
                clicks      = random.randint(10, min(impressions, 500))
                atc         = random.randint(1, max(clicks // 5, 1))
                orders      = random.randint(0, atc)
                ad_spend    = round(random.uniform(50, 2000), 2)
                rows.append({
                    "SKU":              sku,
                    "Marketplace":      mp,
                    "Date":             dt,
                    "Impressions":      impressions,
                    "Clicks":           clicks,
                    "Add to Cart":      atc,
                    "Orders":           orders,
                    "Ad Spend":         ad_spend,
                    "Revenue from Ads": round(orders * random.uniform(299, 2000), 2),
                })
    return pd.DataFrame(rows)


def make_logistics(n=150) -> pd.DataFrame:
    statuses = ["delivered", "delivered", "in_transit", "rto", "pending"]
    rows = []
    for i in range(n):
        dispatch = date.fromisoformat(random_date(20))
        expected = dispatch + timedelta(days=random.randint(3, 7))
        actual   = dispatch + timedelta(days=random.randint(2, 10))
        status   = random.choice(statuses)
        rows.append({
            "Order ID":          f"ORD-{random.randint(1, 200):06d}",
            "Marketplace":       random.choice(MARKETPLACES),
            "Courier":           random.choice(["Delhivery", "Bluedart", "Xpressbees", "DTDC"]),
            "Tracking ID":       f"TRK{random.randint(100000, 999999)}",
            "Fulfillment Type":  random.choice(["seller", "marketplace"]),
            "Warehouse ID":      random.choice(["BOM-WH1", "DEL-WH2", "BLR-WH3"]),
            "Dispatch Date":     dispatch.isoformat(),
            "Expected Delivery": expected.isoformat(),
            "Actual Delivery":   actual.isoformat() if status == "delivered" else "",
            "Shipping Days":     (actual - dispatch).days if status == "delivered" else None,
            "Delivery Status":   status,
            "RTO":               status == "rto",
            "RTO Reason":        "Customer refused" if status == "rto" else "",
            "Snapshot Date":     TODAY.isoformat(),
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", default="sample_data")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    files = {
        "orders.xlsx":    make_orders(),
        "inventory.xlsx": make_inventory(),
        "pricing.xlsx":   make_pricing(),
        "traffic.xlsx":   make_traffic(),
        "logistics.xlsx": make_logistics(),
    }

    for filename, df in files.items():
        path = os.path.join(args.output_dir, filename)
        df.to_excel(path, index=False)
        print(f"  Created {path}  ({len(df)} rows)")

    print(f"\nSample data written to {args.output_dir}/")
    print(f"Seller ID: {SELLER_ID}")
    print(f"Snapshot Date: {TODAY.isoformat()}")


if __name__ == "__main__":
    main()
