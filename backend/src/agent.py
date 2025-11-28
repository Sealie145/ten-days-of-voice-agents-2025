# food_agent_sqlite.py
"""
Day 7 – Food & Grocery Ordering Voice Agent (SQLite) - Indian Context
- Uses SQLite DB 'order_db.sqlite'
- Seeds Indian catalog (Britannia, Amul, Haldiram, Everest, etc.)
- Tools:
    - find_item (search catalog)
    - add_to_cart / remove_from_cart / update_cart / show_cart
    - add_recipe (ingredients for Breakfast, Sandwich, Aloo Paratha, etc.)
    - place_order (Trigger auto-status update simulation)
    - cancel_order (New Feature)
    - get_order_status / order_history
- Auto-simulation: Status updates every 5 seconds in background.
"""

import json
import logging
import os
import sqlite3
import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Annotated

from dotenv import load_dotenv
from pydantic import Field
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)

from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# -------------------------
# Logging
# -------------------------
logger = logging.getLogger("food_agent_sqlite")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

load_dotenv(".env.local")

# -------------------------
# DB config & seeding
# -------------------------
DB_FILE = "order_db.sqlite"


def get_db_path() -> str:
    """Return absolute path for the DB file. If __file__ is not defined (interactive), fall back to cwd."""
    try:
        base = os.path.abspath(os.path.dirname(__file__))
    except NameError:
        base = os.getcwd()
    # ensure directory exists
    if not os.path.isdir(base):
        os.makedirs(base, exist_ok=True)
    return os.path.join(base, DB_FILE)


def get_conn():
    path = get_db_path()
    # check_same_thread=False required for async background tasks accessing DB
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def seed_database():
    """Create tables and seed the Indian catalog if empty."""
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Create catalog table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS catalog (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                price REAL NOT NULL,
                brand TEXT,
                size TEXT,
                units TEXT,
                tags TEXT -- JSON encoded list
            )
        """)

        # Orders table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                timestamp TEXT,
                total REAL,
                customer_name TEXT,
                address TEXT,
                status TEXT DEFAULT 'received',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Order items
        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                item_id TEXT,
                name TEXT,
                unit_price REAL,
                quantity INTEGER,
                notes TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(order_id) ON DELETE CASCADE
            )
        """)

        # Check if catalog empty
        cur.execute("SELECT COUNT(1) FROM catalog")
        if cur.fetchone()[0] == 0:
            catalog = [
                # Oils & Ghee
("oil-sunflower-1l", "Fortune Sunflower Oil", "Oils", 150.00, "Fortune", "1L", "bottle", json.dumps(["cooking", "essential"])),
("ghee-amul-500ml", "Amul Pure Ghee", "Oils", 330.00, "Amul", "500ml", "jar", json.dumps(["ghee", "premium"])),

# Spices
("haldi-200g", "Everest Turmeric Powder", "Spices", 48.00, "Everest", "200g", "pack", json.dumps(["spices"])),
("mirchi-200g", "Everest Red Chilli Powder", "Spices", 75.00, "Everest", "200g", "pack", json.dumps(["spices", "spicy"])),
("jeera-100g", "Catch Cumin Seeds", "Spices", 80.00, "Catch", "100g", "pack", json.dumps(["spices"])),

# Personal Care
("soap-lifebuoy", "Lifebuoy Total Soap", "Personal Care", 38.00, "Lifebuoy", "125g", "bar", json.dumps(["hygiene"])),
("shampoo-sunsilk-180ml", "Sunsilk Black Shine Shampoo", "Personal Care", 110.00, "Sunsilk", "180ml", "bottle", json.dumps(["haircare"])),
("toothpaste-colgate-100g", "Colgate Strong Teeth", "Personal Care", 55.00, "Colgate", "100g", "tube", json.dumps(["hygiene"])),

# Cleaning Supplies
("detergent-surf-1kg", "Surf Excel Easy Wash", "Cleaning", 125.00, "Surf Excel", "1kg", "pack", json.dumps(["cleaning", "laundry"])),
("dishwash-vim-500ml", "Vim Liquid", "Cleaning", 110.00, "Vim", "500ml", "bottle", json.dumps(["cleaning", "kitchen"])),

# Bread & Bakery
("bread-white", "Britannia White Bread", "Bakery", 45.00, "Britannia", "450g", "pack", json.dumps(["breakfast"])),
("brown-bread", "Modern Brown Bread", "Bakery", 55.00, "Modern", "400g", "pack", json.dumps(["breakfast", "healthy"])),

# Beverages (Extras)
("coffee-bru-50g", "Bru Instant Coffee", "Beverages", 160.00, "Bru", "50g", "jar", json.dumps(["coffee"])),
("coke-750ml", "Coca-Cola", "Beverages", 45.00, "Coke", "750ml", "bottle", json.dumps(["soft-drink"])),

# Frozen / Ready to Cook
("paratha-aloo-5pc", "Haldiram Aloo Paratha", "Frozen", 130.00, "Haldiram", "5pcs", "pack", json.dumps(["frozen", "quick-meal"])),
("nuggets-veg-500g", "Yummiez Veg Nuggets", "Frozen", 160.00, "Yummiez", "500g", "pack", json.dumps(["frozen", "snack"])),

# Eggs (You missed this but it's essential)
("eggs-6pc", "Fresh Hen Eggs", "Dairy & Eggs", 40.00, "", "6pcs", "pack", json.dumps(["protein", "essential"])),

# Fruits
("banana-1dz", "Fresh Bananas", "Fruits", 55.00, "", "1 dozen", "dozen", json.dumps(["fruit", "healthy"])),
("apple-1kg", "Kashmiri Apples", "Fruits", 160.00, "", "1kg", "kg", json.dumps(["fruit", "premium"])),

# Misc Essentials
("matchbox-1pc", "Safety Matches", "Essentials", 10.00, "Homelites", "1pc", "box", json.dumps(["essential"])),
("tissue-100pulls", "Origami Tissue Box", "Essentials", 55.00, "Origami", "100 pulls", "box", json.dumps(["hygiene"])),

            ]
            cur.executemany("""
                INSERT INTO catalog (id, name, category, price, brand, size, units, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, catalog)
            conn.commit()
            logger.info(f"✅ Seeded Indian catalog into {get_db_path()}")

        conn.close()
    except Exception as e:
        logger.exception("Failed to seed database: %s", e)


# Seed DB on import/run (safe to call multiple times)
seed_database()

# -------------------------
# In-memory per-session cart
# -------------------------
@dataclass
class CartItem:
    item_id: str
    name: str
    unit_price: float
    quantity: int = 1
    notes: str = ""

@dataclass
class Userdata:
    cart: List[CartItem] = field(default_factory=list)
    customer_name: Optional[str] = None

# -------------------------
# DB Helpers
# -------------------------

def find_catalog_item_by_id_db(item_id: str) -> Optional[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM catalog WHERE LOWER(id) = LOWER(?) LIMIT 1", (item_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    record = dict(row)
    try:
        record["tags"] = json.loads(record.get("tags") or "[]")
    except Exception:
        record["tags"] = []
    return record


def search_catalog_by_name_db(query: str) -> List[dict]:
    q = f"%{query.lower()}%"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM catalog
        WHERE LOWER(name) LIKE ? OR LOWER(tags) LIKE ?
        LIMIT 50
    """, (q, q))
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows:
        rec = dict(r)
        try:
            rec["tags"] = json.loads(rec.get("tags") or "[]")
        except Exception:
            rec["tags"] = []
        results.append(rec)
    return results


def insert_order_db(order_id: str, timestamp: str, total: float, customer_name: str, address: str, status: str, items: List[CartItem]):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (order_id, timestamp, total, customer_name, address, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (order_id, timestamp, total, customer_name, address, status))
    for ci in items:
        cur.execute("""
            INSERT INTO order_items (order_id, item_id, name, unit_price, quantity, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (order_id, ci.item_id, ci.name, ci.unit_price, ci.quantity, ci.notes))
    conn.commit()
    conn.close()


def get_order_db(order_id: str) -> Optional[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE order_id = ? LIMIT 1", (order_id,))
    o = cur.fetchone()
    if not o:
        conn.close()
        return None
    order = dict(o)
    cur.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    items = [dict(r) for r in cur.fetchall()]
    conn.close()
    order["items"] = items
    return order


def list_orders_db(limit: int = 10, customer_name: Optional[str] = None) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    if customer_name:
        cur.execute("SELECT * FROM orders WHERE LOWER(customer_name) = LOWER(?) ORDER BY created_at DESC LIMIT ?", (customer_name, limit))
    else:
        cur.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def update_order_status_db(order_id: str, new_status: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = ?, updated_at = datetime('now') WHERE order_id = ?", (new_status, order_id))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0

# -------------------------
# LOGIC & ASYNC SIMULATION
# -------------------------

# Recipe map for "Add Recipe" tool
RECIPE_MAP = {
    "breakfast": ["bread-white", "eggs-6pc", "banana-1dz"],
    "healthy breakfast": ["brown-bread", "eggs-6pc", "apple-1kg"],
    "sandwich": ["bread-white", "eggs-6pc"],
    "egg sandwich": ["bread-white", "eggs-6pc"],
    "coffee": ["coffee-bru-50g"],
    "morning coffee": ["coffee-bru-50g"],
    "quick meal": ["paratha-aloo-5pc"],
    "aloo paratha": ["paratha-aloo-5pc", "ghee-amul-500ml"],
    "snack": ["nuggets-veg-500g"],
    "veg nuggets": ["nuggets-veg-500g", "coke-750ml"],
    "fruit bowl": ["banana-1dz", "apple-1kg"],
    "cooking basics": ["oil-sunflower-1l", "jeera-100g", "haldi-200g", "mirchi-200g"],
    "indian spices": ["jeera-100g", "haldi-200g", "mirchi-200g"],
    "spice kit": ["jeera-100g", "haldi-200g", "mirchi-200g"],
}

# Intelligent ingredient inference helpers
import re

_NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
}

def _parse_servings_from_text(text: str) -> int:
    """Try to extract servings/quantity from informal text like 'for two people' or 'for 3'. Default 1."""
    text = (text or "").lower()
    m = re.search(r"for\s+(\d+)\s*(?:people|person|servings)?", text)
    if m:
        try:
            return max(1, int(m.group(1)))
        except Exception:
            pass
    for word, num in _NUMBER_WORDS.items():
        if f"for {word}" in text:
            return num
    return 1


def _infer_items_from_tags(query: str, max_results: int = 6) -> List[str]:
    """Try to infer catalog items by matching query words to tags in the catalog. Returns list of item_ids."""
    words = re.findall(r"\w+", (query or "").lower())
    found = []
    conn = get_conn()
    cur = conn.cursor()
    for w in words:
        if len(found) >= max_results:
            break
        q = f"%\"{w}\"%"
        cur.execute("SELECT * FROM catalog WHERE LOWER(tags) LIKE ? OR LOWER(name) LIKE ? LIMIT 10", (q, f"%{w}%"))
        rows = cur.fetchall()
        for r in rows:
            rid = r["id"]
            if rid not in found:
                found.append(rid)
                if len(found) >= max_results:
                    break
    conn.close()
    return found

STATUS_FLOW = ["received", "confirmed", "shipped", "out_for_delivery", "delivered"]


async def simulate_delivery_flow(order_id: str):
    """
    Background task: automatically advances order status every 5 seconds.
    Flow: received -> confirmed -> shipped -> out_for_delivery -> delivered
    """
    logger.info(f"🔄 [Simulation] Started tracking simulation for {order_id}")

    # initial wait
    await asyncio.sleep(5)

    # Loop through statuses starting from index 1 (confirmed)
    for next_status in STATUS_FLOW[1:]:
        # Check if order was cancelled in the meantime
        curr_order = get_order_db(order_id)
        if curr_order and curr_order.get("status") == "cancelled":
            logger.info(f"🛑 [Simulation] Order {order_id} was cancelled. Stopping simulation.")
            return

        update_order_status_db(order_id, next_status)
        logger.info(f"🚚 [Simulation] Order {order_id} updated to '{next_status}'")
        await asyncio.sleep(5)

    logger.info(f"✅ [Simulation] Order {order_id} simulation complete (Delivered).")


def cart_total(cart: List[CartItem]) -> float:
    return round(sum(ci.unit_price * ci.quantity for ci in cart), 2)

# -------------------------
# AGENT TOOLS
# -------------------------
@function_tool
async def find_item(
    ctx: RunContext[Userdata],
    query: Annotated[str, Field(description="Name or partial name of item (e.g., 'milk', 'paneer')")],
) -> str:
    matches = search_catalog_by_name_db(query)
    if not matches:
        return f"No items found matching '{query}'. Try generic names like 'milk' or 'rice'."
    lines = []
    for it in matches[:10]:
        lines.append(f"- {it['name']} (id: {it['id']}) — ₹{it['price']:.2f} — {it.get('size','')}")
    return "Found:\n" + "\n".join(lines)


@function_tool
async def add_to_cart(
    ctx: RunContext[Userdata],
    item_id: Annotated[str, Field(description="Catalog item id")],
    quantity: Annotated[int, Field(description="Quantity", default=1)] = 1,
    notes: Annotated[str, Field(description="Optional notes")] = "",
) -> str:
    item = find_catalog_item_by_id_db(item_id)
    if not item:
        return f"Item id '{item_id}' not found."

    for ci in ctx.userdata.cart:
        if ci.item_id.lower() == item_id.lower():
            ci.quantity += quantity
            if notes:
                ci.notes = notes
            total = cart_total(ctx.userdata.cart)
            return f"Updated '{ci.name}' quantity to {ci.quantity}. Cart total: \u20B9{total:.2f}"

    ci = CartItem(item_id=item["id"], name=item["name"], unit_price=float(item["price"]), quantity=quantity, notes=notes)
    ctx.userdata.cart.append(ci)
    total = cart_total(ctx.userdata.cart)
    return f"Added {quantity} x '{item['name']}' to cart. Cart total: \u20B9{total:.2f}"


@function_tool
async def remove_from_cart(
    ctx: RunContext[Userdata],
    item_id: Annotated[str, Field(description="Catalog item id to remove")],
) -> str:
    before = len(ctx.userdata.cart)
    ctx.userdata.cart = [ci for ci in ctx.userdata.cart if ci.item_id.lower() != item_id.lower()]
    after = len(ctx.userdata.cart)
    if before == after:
        return f"Item '{item_id}' was not in your cart."
    total = cart_total(ctx.userdata.cart)
    return f"Removed item '{item_id}' from cart. Cart total: \u20B9{total:.2f}"


@function_tool
async def update_cart_quantity(
    ctx: RunContext[Userdata],
    item_id: Annotated[str, Field(description="Catalog item id to update")],
    quantity: Annotated[int, Field(description="New quantity")],
) -> str:
    if quantity < 1:
        return await remove_from_cart(ctx, item_id)
    for ci in ctx.userdata.cart:
        if ci.item_id.lower() == item_id.lower():
            ci.quantity = quantity
            total = cart_total(ctx.userdata.cart)
            return f"Updated '{ci.name}' quantity to {ci.quantity}. Cart total: \u20B9{total:.2f}"
    return f"Item '{item_id}' not found in cart."


@function_tool
async def show_cart(ctx: RunContext[Userdata]) -> str:
    if not ctx.userdata.cart:
        return "Your cart is empty."
    lines = []
    for ci in ctx.userdata.cart:
        lines.append(f"- {ci.quantity} x {ci.name} @ \u20B9{ci.unit_price:.2f} each = \u20B9{ci.unit_price * ci.quantity:.2f}")
    total = cart_total(ctx.userdata.cart)
    return "Your cart:\n" + "\n".join(lines) + f"\nTotal: \u20B9{total:.2f}"


@function_tool
async def add_recipe(
    ctx: RunContext[Userdata],
    dish_name: Annotated[str, Field(description="Name of dish, e.g. 'chai', 'maggi', 'dal chawal'")],
) -> str:
    key = dish_name.strip().lower()
    if key not in RECIPE_MAP:
        return f"Sorry, I don't have a recipe for '{dish_name}'. Try 'chai', 'maggi' or 'paneer butter masala'."
    added = []
    for item_id in RECIPE_MAP[key]:
        item = find_catalog_item_by_id_db(item_id)
        if not item:
            continue

        found = False
        for ci in ctx.userdata.cart:
            if ci.item_id.lower() == item_id.lower():
                ci.quantity += 1
                found = True
                break
        if not found:
            ctx.userdata.cart.append(CartItem(item_id=item["id"], name=item["name"], unit_price=float(item["price"]), quantity=1))
        added.append(item["name"])

    total = cart_total(ctx.userdata.cart)
    return f"Added ingredients for '{dish_name}': {', '.join(added)}. Cart total: \u20B9{total:.2f}"


@function_tool
async def ingredients_for(
    ctx: RunContext[Userdata],
    request: Annotated[str, Field(description="Natural language request, e.g. 'ingredients for peanut butter sandwich for two'")],
) -> str:
    """Handle high-level ingredient requests like 'ingredients for peanut butter sandwich' or 'get me pasta for two people'.
    Attempts a map lookup first, then falls back to tag inference.
    """
    text = (request or "").strip()
    servings = _parse_servings_from_text(text)

    # try to extract a dish phrase after common verbs
    m = re.search(r"ingredients? for (.+)", text, re.I)
    if m:
        dish = m.group(1)
    else:
        m2 = re.search(r"(?:make|for making|get me what i need for|i need) (.+)", text, re.I)
        dish = m2.group(1) if m2 else text

    # remove trailing 'for X people' fragments
    dish = re.sub(r"for\s+\w+(?: people| person| persons)?", "", dish, flags=re.I).strip()
    key = dish.lower()

    item_ids = []
    if key in RECIPE_MAP:
        item_ids = RECIPE_MAP[key]
    else:
        item_ids = _infer_items_from_tags(dish)

    if not item_ids:
        return f"Sorry, I couldn't determine ingredients for '{request}'. Try phrases like 'breakfast', 'sandwich', 'cooking basics', or 'indian spices'."

    added = []
    for iid in item_ids:
        item = find_catalog_item_by_id_db(iid)
        if not item:
            continue
        # add with servings as quantity
        found = False
        for ci in ctx.userdata.cart:
            if ci.item_id.lower() == iid.lower():
                ci.quantity += servings
                found = True
                break
        if not found:
            ctx.userdata.cart.append(CartItem(item_id=item['id'], name=item['name'], unit_price=float(item['price']), quantity=servings))
        added.append(item['name'])

    total = cart_total(ctx.userdata.cart)
    return f"I've added {', '.join(added)} to your cart for '{dish}'. (Servings: {servings}). Cart total: ₹{total:.2f}"


@function_tool
async def place_order(
    ctx: RunContext[Userdata],
    customer_name: Annotated[str, Field(description="Customer name")],
    address: Annotated[str, Field(description="Delivery address")],
) -> str:
    if not ctx.userdata.cart:
        return "Your cart is empty."

    order_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat() + "Z"
    total = cart_total(ctx.userdata.cart)

    # 1. Persist to DB
    insert_order_db(order_id=order_id, timestamp=now, total=total, customer_name=customer_name, address=address, status="received", items=ctx.userdata.cart)

    # 2. Clear Cart
    ctx.userdata.cart = []
    ctx.userdata.customer_name = customer_name

    # 3. Trigger Background Simulation (Received -> Shipped -> Out for delivery...)
    try:
        # create a background task on the running event loop
        asyncio.create_task(simulate_delivery_flow(order_id))
    except RuntimeError:
        # If there is no running loop, schedule on a new loop in a background thread
        loop = asyncio.new_event_loop()
        asyncio.get_running_loop() if asyncio.get_event_loop().is_running() else None
        # fire-and-forget: run in background
        asyncio.get_event_loop().call_soon_threadsafe(lambda: asyncio.create_task(simulate_delivery_flow(order_id)))

    return f"Order placed successfully! Order ID: {order_id}. Total: \u20B9{total:.2f}. I have initiated express shipping; the status will update automatically shortly."


@function_tool
async def cancel_order(
    ctx: RunContext[Userdata],
    order_id: Annotated[str, Field(description="Order ID to cancel")],
) -> str:
    o = get_order_db(order_id)
    if not o:
        return f"No order found with id {order_id}."

    status = o.get("status", "")
    if status == "delivered":
        return f"Order {order_id} has already been delivered and cannot be cancelled."

    if status == "cancelled":
        return f"Order {order_id} is already cancelled."

    # Update DB
    update_order_status_db(order_id, "cancelled")
    return f"Order {order_id} has been cancelled successfully."


@function_tool
async def get_order_status(
    ctx: RunContext[Userdata],
    order_id: Annotated[str, Field(description="Order ID to check")],
) -> str:
    o = get_order_db(order_id)
    if not o:
        return f"No order found with id {order_id}."
    return f"Order {order_id} status: {o.get('status', 'unknown')}. Updated at: {o.get('updated_at')}"


@function_tool
async def order_history(
    ctx: RunContext[Userdata],
    customer_name: Annotated[Optional[str], Field(description="Optional customer name to filter", default=None)] = None,
) -> str:
    rows = list_orders_db(limit=5, customer_name=customer_name)
    if not rows:
        return "No orders found."
    lines = []
    for o in rows:
        lines.append(f"- {o['order_id']} | \u20B9{o['total']:.2f} | Status: {o.get('status')}")
    prefix = "Recent Orders"
    if customer_name:
        prefix += f" for {customer_name}"
    return prefix + ":\n" + "\n".join(lines)

# -------------------------
# Agent Definition
# -------------------------
class FoodAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are 'Robin', a helpful assistant for 'Zepto Shop', an Indian grocery store.
            Currency is Indian Rupees (₹).
            
            Capabilities:
            1. Catalog: Search for items like bread, eggs, coffee, spices, fruits, frozen foods, cleaning supplies, and personal care.
            2. Cart: Add/Remove items, Update quantities, Show cart with totals.
            3. Recipes: Add ingredients for meals like breakfast, sandwich, aloo paratha, cooking basics, indian spices, fruit bowl.
            4. Orders: Place orders with customer name and address.
            5. Tracking: Check order status (auto-updates every 5 seconds: received → confirmed → shipped → out_for_delivery → delivered).
            6. Cancellation: Cancel orders if not yivered.
            7. History: View past orders.
            
            Available items include:
            - Bakery: White bread, brown bread
            - Beverages: Coffee, Coca-Cola
            - Dairy & Eggs: Fresh eggs
            - Fruits: Bananas, apples
            - Frozen: Aloo paratha, veg nuggets
            - Oils: Sunflower oil, ghee
            - Spices: Turmeric, red chilli, cumin
            - Personal Care: Soap, shampoo, toothpaste
            - Cleaning: Detergent, dishwash liquid
            - Essentials: Matches, tissues
            
            When placing an order, mention that express tracking is enabled.
            If user asks "Where is my order?", check status and explain it updates automatically.
            """,
            tools=[find_item, add_to_cart, remove_from_cart, update_cart_quantity, show_cart, add_recipe, place_order, cancel_order, get_order_status, order_history],
        )

# -------------------------
# Entrypoint
# -------------------------
def prewarm(proc: JobProcess):
    # load VAD model and stash on process userdata
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        logger.warning("VAD prewarm failed; continuing without preloaded VAD.")


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info("\n" + "🛒" * 12)
    logger.info("STARTING ZEPTO SHOP - Voice Grocery Ordering (Auto-Tracking Enabled)")

    userdata = Userdata()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-marcus",
            style="Conversational",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata.get("vad"),
        userdata=userdata,
    )

    await session.start(
        agent=FoodAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))