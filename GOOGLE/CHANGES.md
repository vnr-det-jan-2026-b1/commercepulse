# CommercePulse — Change Log

## [Latest] Product Images + Stock Room + Restock System

---

### 1. Local Product Images

**Problem:** Product images were Unsplash CDN URLs — inconsistent quality, shared IDs between products, and no dark-background aesthetic.

**Solution:** All 12 product images replaced with dark-background studio photography saved locally in `storefront/public/products/`.

| Product ID | File | Product |
|---|---|---|
| P001 | `public/products/p001.jpg` | Wireless Earbuds Pro |
| P002 | `public/products/p002.jpg` | 20W Fast Charger |
| P003 | `public/products/p003.png` | Smartwatch Series X |
| P004 | `public/products/p004.jpg` | Mechanical Keyboard |
| P005 | `public/products/p005.jpg` | Portable Power Bank 20000mAh |
| P006 | `public/products/p006.jpg` | Noise-Cancelling Headphones |
| P007 | `public/products/p007.jpg` | Portable Bluetooth Speaker |
| P008 | `public/products/p008.jpg` | USB-C Hub 7-in-1 |
| P009 | `public/products/p009.jpg` | Gaming Mouse RGB |
| P010 | `public/products/p010.jpg` | 4K Webcam Pro |
| P011 | `public/products/p011.jpg` | Fitness Tracker Band |
| P012 | `public/products/p012.jpg` | Smart LED Desk Lamp |

**Files changed:**
- `storefront/src/data/products.ts` — all `image` fields updated from Unsplash URLs to `/products/pXXX.jpg`
- `storefront/public/products/` — new directory containing all 12 product images

---

### 2. Stock Room Tab (Admin Dashboard)

A dedicated **Stock Room** tab was added to the NovaAdmin sidebar, sitting between Recommendations and Products.

#### Sidebar
- New "Stock Room" nav item with a warehouse/box SVG icon
- **Amber badge** on the sidebar item showing the count of products at ≤ 3 units so the admin is immediately aware without opening the tab

#### Stock Room Tab Contents

**Summary KPI Row (4 cards):**
| Card | Value |
|---|---|
| Total Products | Count of all products |
| Healthy Stock | Products with > 3 units |
| Low Stock (≤3) | Products with 1–3 units remaining |
| Out of Stock | Products with 0 units |

**"Needs Restocking" Section:**
- Shown only when 1+ products are at ≤ 3 units
- Displays a 2-column grid of product cards, each showing:
  - Status badge: `● Out of Stock` (red) or `● Low Stock` (amber)
  - Product name, category, price
  - Large unit count number (color-coded red/amber)
  - Visual stock level progress bar (fill = `current / initial`)
  - Units sold count
  - **Restock quantity input** (number field, min 1, default 10)
  - **"Confirm Restock"** button → calls the restock API
  - On success: shows `✓ +N units ordered` confirmation

**All Products Table:**
- Full inventory table sorted by stock level (lowest first)
- Columns: Product, Category, Price, Sold, Stock Level (bar + fraction), Status, Action
- Action column: shows qty input + `+Add` button for critical items only; `—` for healthy products
- After restock: shows `✓ +N` confirmation in the action cell

---

### 3. Restock Alerts in Recommendations Tab

When any product drops to ≤ 3 units, a **yellow alert banner** appears at the top of the Recommendations tab (above the demand-based insights grid):

- Header: `● RESTOCK ALERTS — X products critically low`
- One row per critical product showing:
  - Product name + stock status (`● Out of stock` / `● Only N units remaining`)
  - Category label
  - Quantity number input
  - **Restock** button (calls API)
  - **Dismiss** button (hides the alert for this product in the current session)
- After restock: row shows `✓ +N units ordered`

---

### 4. Restock API — Backend

#### New Endpoint: `POST /v1/analytics/stock/restock`

**Request body:**
```json
{
  "seller_id": "SELLER_001",
  "product_id": "P006",
  "quantity": 25
}
```

**What it does:**
1. Runs a BigQuery DML `UPDATE` on `cp_raw.product_catalog`:
   ```sql
   UPDATE `cp_raw.product_catalog`
   SET initial_stock = initial_stock + @quantity
   WHERE product_id = @product_id
     AND seller_id  = @seller_id
   ```
2. Queries the updated stock for the product
3. Returns `{ ok, product_id, quantity_added, updated }` where `updated` is the new stock row

**How stock is calculated:**
`current_stock = initial_stock - units_sold (from purchase events)`
So increasing `initial_stock` directly raises `current_stock` across all queries that depend on it (stock endpoint, recommendations, dashboard KPIs).

**Files changed:**
- `backend/app/routes/analytics.py` — added `RestockRequest` Pydantic model + `POST /stock/restock` route
- `backend/app/services/analytics_queries.py` — added `RESTOCK_SQL` DML query constant

---

### 5. Admin Frontend — Restock Integration

**Files changed:**
- `frontend/src/api/client.ts` — added `restockProduct(productId, quantity)` function
- `frontend/src/hooks/useAnalytics.ts` — added `useRestock()` mutation hook using `@tanstack/react-query`'s `useMutation`
- `frontend/src/pages/Dashboard.tsx` — full Stock Room tab implementation + restock UI

#### State management in Dashboard:
| State | Type | Purpose |
|---|---|---|
| `restockQty` | `Record<string, number>` | Tracks qty input value per product |
| `restockDone` | `Record<string, number>` | Stores confirmed restock qty after success |
| `restockDismissed` | `Set<string>` | Hides alert banner rows (session-only) |

#### Cache invalidation on restock success:
```ts
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['stock'] });
  queryClient.invalidateQueries({ queryKey: ['recommendations'] });
}
```
This causes the stock table, KPI cards, and recommendations to re-fetch immediately after a restock, so the admin sees updated numbers without a page refresh.

---

### 6. Storefront — Live Stock Polling

**File changed:** `storefront/src/App.tsx`

The storefront already fetched stock from the backend on mount and used it to:
- Show stock-based badges on product cards
- Disable "Add to Cart" for out-of-stock items

A **30-second polling interval** was added so that when an admin restocks a product, the storefront automatically reflects it within 30 seconds — no page refresh needed.

```ts
useEffect(() => {
  refreshStock();
  const interval = setInterval(refreshStock, 30_000);
  return () => clearInterval(interval);
}, []);
```

---

### End-to-End Restock Flow

```
Admin opens Stock Room tab
  → Sees product with 2 units left (amber badge)
  → Types "50" in the qty input
  → Clicks "Confirm Restock"
    → POST /v1/analytics/stock/restock { product_id, quantity: 50 }
      → BigQuery UPDATE: initial_stock += 50
    → React Query invalidates ['stock'] + ['recommendations']
      → Dashboard KPIs, stock table, sidebar badge all update instantly
  → Card shows "✓ +50 units ordered"

Storefront (within 30s)
  → GET /v1/analytics/stock re-fetches
  → Product now shows "In Stock" badge
  → "Add to Cart" button re-enabled
```
