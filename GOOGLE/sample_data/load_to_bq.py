import pandas as pd
import subprocess
import os
from datetime import datetime, timezone

base = r'C:\Users\sahit\OneDrive\Desktop\projects\de\commercepulse\GOOGLE\sample_data'
now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
seller_id = 'SELLER_001'

def load(table_name, df):
    df['seller_id'] = seller_id
    df['ingest_timestamp'] = now
    csv_path = os.path.join(base, table_name + '_clean.csv')
    df.to_csv(csv_path, index=False)
    print(f'  {len(df)} rows -> {csv_path}')
    cmd = (
        f'bq load --replace --autodetect --source_format=CSV '
        f'--location=asia-south1 '
        f'commercepulse-project:cp_raw.{table_name} "{csv_path}"'
    )
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode == 0:
        print(f'  Loaded cp_raw.{table_name}')
    else:
        print(f'  ERROR: {result.stderr}')

# ── inventory ────────────────────────────────────────────────────────────────
print('inventory...')
df = pd.read_excel(os.path.join(base, 'inventory.xlsx'))
df = df.rename(columns={
    'SKU':               'sku',
    'Marketplace':       'marketplace',
    'Available Stock':   'available_stock',
    'Reserved Stock':    'reserved_stock',
    'Reorder Threshold': 'reorder_threshold',
    'Days of Stock':     'days_of_stock',
    'Warehouse':         'warehouse_location',
    'Snapshot Date':     'snapshot_date',
})
load('inventory', df)

# ── logistics ────────────────────────────────────────────────────────────────
print('logistics...')
df = pd.read_excel(os.path.join(base, 'logistics.xlsx'))
df = df.rename(columns={
    'Order ID':           'external_order_id',
    'Marketplace':        'marketplace',
    'Courier':            'courier_name',
    'Tracking ID':        'tracking_id',
    'Fulfillment Type':   'fulfillment_type',
    'Warehouse ID':       'warehouse_id',
    'Dispatch Date':      'dispatch_date',
    'Expected Delivery':  'expected_delivery',
    'Actual Delivery':    'actual_delivery',
    'Shipping Days':      'shipping_time_days',
    'Delivery Status':    'delivery_status',
    'RTO':                'rto_flag',
    'RTO Reason':         'rto_reason',
    'Snapshot Date':      'snapshot_date',
})
# normalise rto_flag to boolean
df['rto_flag'] = df['rto_flag'].map(
    lambda x: True if str(x).strip().lower() in ('1', 'true', 'yes') else False
)
load('logistics', df)

# ── traffic ──────────────────────────────────────────────────────────────────
print('traffic...')
df = pd.read_excel(os.path.join(base, 'traffic.xlsx'))
df = df.rename(columns={
    'SKU':              'sku',
    'Marketplace':      'marketplace',
    'Date':             'metric_date',
    'Impressions':      'impressions',
    'Clicks':           'clicks',
    'Add to Cart':      'add_to_cart',
    'Orders':           'orders',
    'Ad Spend':         'ad_spend',
    'Revenue from Ads': 'revenue_from_ads',
})
load('traffic', df)

# ── orders ───────────────────────────────────────────────────────────────────
print('orders...')
df = pd.read_excel(os.path.join(base, 'orders.xlsx'))
df = df.rename(columns={
    'Order ID':            'external_order_id',
    'Marketplace':         'marketplace',
    'SKU':                 'sku',
    'Status':              'order_status',
    'Quantity':            'quantity',
    'Selling Price':       'selling_price',
    'Cost Price':          'cost_price',
    'Discount':            'discount',
    'Tax':                 'tax',
    'Shipping Fee':        'shipping_fee',
    'Order Date':          'order_date',
    'Delivery Date':       'delivery_date',
    'Return':              'return_flag',
    'Cancellation Reason': 'cancellation_reason',
})
df['net_revenue'] = (
    df['selling_price'] * df['quantity'] - df['discount']
).round(2)
df['return_flag'] = df['return_flag'].map(
    lambda x: True if str(x).strip().lower() in ('1', 'true', 'yes') else False
)
load('orders', df)

# ── pricing ──────────────────────────────────────────────────────────────────
print('pricing...')
df = pd.read_excel(os.path.join(base, 'pricing.xlsx'))
df = df.rename(columns={
    'SKU':               'sku',
    'Marketplace':       'marketplace',
    'Selling Price':     'selling_price',
    'Cost Price':        'cost_price',
    'MRP':               'mrp',
    'Commission %':      'commission_pct',
    'Commission Amount': 'commission_amount',
    'Discount %':        'discount_pct',
    'Net Margin':        'net_margin',
    'Margin %':          'margin_pct',
    'Snapshot Date':     'snapshot_date',
})
load('pricing', df)

# ── product_catalog ──────────────────────────────────────────────────────────
print('product_catalog...')
product_rows = [
    {"product_id": "P001", "product_name": "Wireless Earbuds Pro",       "category": "Audio",       "price": 2999, "initial_stock": 10, "description": "30hr battery · Active Noise Cancellation · IPX5 waterproof · Touch controls · 10-min fast charge = 2hr play",                                    "image_path": "/products/p001.jpg", "rating": 4.5, "reviews": 2847, "badge": "Best Seller"},
    {"product_id": "P002", "product_name": "20W Fast Charger",           "category": "Accessories", "price":  799, "initial_stock": 10, "description": "GaN III technology · USB-C Power Delivery · Foldable prongs · Universal compatibility · Charges phone to 50% in 30 min",                    "image_path": "/products/p002.jpg", "rating": 4.3, "reviews": 1203, "badge": ""},
    {"product_id": "P003", "product_name": "Smartwatch Series X",        "category": "Wearables",   "price": 8499, "initial_stock": 10, "description": "1.45\" AMOLED always-on · GPS · SpO2 + heart rate · 7-day battery · 50m water resistant · Aluminium case",                                    "image_path": "/products/p003.png", "rating": 4.6, "reviews": 5120, "badge": "New"},
    {"product_id": "P004", "product_name": "Mechanical Keyboard",        "category": "Peripherals", "price": 3499, "initial_stock": 10, "description": "TKL 87-key · Red linear switches · Per-key RGB · USB-C detachable cable · Aluminium top plate · N-key rollover",                          "image_path": "/products/p004.jpg", "rating": 4.7, "reviews":  934, "badge": ""},
    {"product_id": "P005", "product_name": "Portable Power Bank 20000mAh","category": "Accessories","price": 1799, "initial_stock": 10, "description": "65W bi-directional PD · Dual USB-C + USB-A · Charges laptop · Digital % display · Slim 15mm profile",                                     "image_path": "/products/p005.jpg", "rating": 4.4, "reviews": 3612, "badge": ""},
    {"product_id": "P006", "product_name": "Noise-Cancelling Headphones","category": "Audio",       "price": 5999, "initial_stock": 10, "description": "40hr ANC playback · Hi-Res Audio certified · Memory foam earcups · Bluetooth 5.3 · Foldable · 3-mode EQ",                                  "image_path": "/products/p006.jpg", "rating": 4.8, "reviews": 7841, "badge": "Top Rated"},
    {"product_id": "P007", "product_name": "Portable Bluetooth Speaker", "category": "Audio",       "price": 2299, "initial_stock": 10, "description": "360 degree surround sound · 24hr battery · IPX7 waterproof · Built-in powerbank · Dual stereo pairing · Bass radiator",                    "image_path": "/products/p007.jpg", "rating": 4.4, "reviews": 2103, "badge": ""},
    {"product_id": "P008", "product_name": "USB-C Hub 7-in-1",           "category": "Accessories", "price": 1499, "initial_stock": 10, "description": "4K HDMI · 100W PD passthrough · USB-A 3.0 x3 · SD + MicroSD slots · Plug and play · Aluminium shell",                                    "image_path": "/products/p008.jpg", "rating": 4.2, "reviews":  876, "badge": "New"},
    {"product_id": "P009", "product_name": "Gaming Mouse RGB",           "category": "Peripherals", "price": 1299, "initial_stock": 10, "description": "16000 DPI optical sensor · 7 programmable buttons · Per-zone RGB · 80hr wireless battery · Ergonomic right-hand grip",                    "image_path": "/products/p009.jpg", "rating": 4.5, "reviews": 1544, "badge": ""},
    {"product_id": "P010", "product_name": "4K Webcam Pro",              "category": "Peripherals", "price": 4999, "initial_stock": 10, "description": "4K 30fps · 1080p 60fps · AI auto-framing · Built-in noise-cancelling mic · Low-light correction · Privacy cover",                         "image_path": "/products/p010.jpg", "rating": 4.3, "reviews":  621, "badge": ""},
    {"product_id": "P011", "product_name": "Fitness Tracker Band",       "category": "Wearables",   "price": 3299, "initial_stock": 10, "description": "1.47\" AMOLED · 14-day battery · 100+ workout modes · 24/7 heart rate and SpO2 · Sleep tracking · 5ATM swim-proof",                        "image_path": "/products/p011.jpg", "rating": 4.4, "reviews": 2890, "badge": ""},
    {"product_id": "P012", "product_name": "Smart LED Desk Lamp",        "category": "Smart Home",  "price": 1999, "initial_stock": 10, "description": "Voice and app control · 4 colour temperatures · 10 brightness levels · USB-A charging port · Eye-care flicker-free · Touch dimmer",        "image_path": "/products/p012.jpg", "rating": 4.3, "reviews": 1102, "badge": ""},
]
df_products = pd.DataFrame(product_rows)
df_products['seller_id'] = seller_id
df_products['ingest_timestamp'] = now
csv_path = os.path.join(base, 'product_catalog_clean.csv')
df_products.to_csv(csv_path, index=False)
print(f'  {len(df_products)} rows -> {csv_path}')
cmd = (
    f'bq load --replace --autodetect --source_format=CSV '
    f'--location=asia-south1 '
    f'commercepulse-project:cp_raw.product_catalog "{csv_path}"'
)
result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
if result.returncode == 0:
    print(f'  Loaded cp_raw.product_catalog')
else:
    print(f'  ERROR: {result.stderr}')

print('\nDone.')
