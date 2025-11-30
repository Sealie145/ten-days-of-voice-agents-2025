

import json
import logging
import os
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Annotated

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
logger = logging.getLogger("voice_game_master")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

load_dotenv(".env.local")

CATALOG = [
    {
        "id": "tee-m-002",
        "name": "H&M Men's Basic Tee",
        "description": "Classic crew neck t-shirt, regular fit.",
        "price": 699,
        "currency": "INR",
        "category": "tshirt",
        "gender": "men",
        "brand": "H&M",
        "color": "white",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "id": "hoodie-m-001",
        "name": "Nike Men's Sportswear Hoodie",
        "description": "Premium fleece hoodie with swoosh logo.",
        "price": 2999,
        "currency": "INR",
        "category": "hoodie",
        "gender": "men",
        "brand": "Nike",
        "color": "grey",
        "sizes": ["M", "L", "XL"],
    },
    {
        "id": "jeans-m-001",
        "name": "Levi's Men's 511 Slim Fit Jeans",
        "description": "Classic slim fit denim jeans.",
        "price": 2799,
        "currency": "INR",
        "category": "jeans",
        "gender": "men",
        "brand": "Levi's",
        "color": "blue",
        "sizes": ["30", "32", "34", "36"],
    },
    {
        "id": "shirt-m-001",
        "name": "Peter England Formal Shirt",
        "description": "Slim fit formal shirt for office wear.",
        "price": 1299,
        "currency": "INR",
        "category": "shirt",
        "gender": "men",
        "brand": "Peter England",
        "color": "white",
        "sizes": ["38", "40", "42", "44"],
    },
    # Women's Wear
    {
        "id": "kurti-w-001",
        "name": "Libas Women's Printed Kurti",
        "description": "Elegant printed kurti for casual wear.",
        "price": 899,
        "currency": "INR",
        "category": "kurti",
        "gender": "women",
        "brand": "Libas",
        "color": "pink",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "id": "dress-w-001",
        "name": "Zara Women's Midi Dress",
        "description": "Stylish midi dress for parties.",
        "price": 2499,
        "currency": "INR",
        "category": "dress",
        "gender": "women",
        "brand": "Zara",
        "color": "black",
        "sizes": ["S", "M", "L"],
    },
    {
        "id": "top-w-001",
        "name": "Forever 21 Crop Top",
        "description": "Trendy crop top for casual outings.",
        "price": 599,
        "currency": "INR",
        "category": "top",
        "gender": "women",
        "brand": "Forever 21",
        "color": "white",
        "sizes": ["S", "M", "L"],
    },
    {
        "id": "jeans-w-001",
        "name": "Levi's Women's Skinny Jeans",
        "description": "Stretchable skinny fit jeans.",
        "price": 2499,
        "currency": "INR",
        "category": "jeans",
        "gender": "women",
        "brand": "Levi's",
        "color": "blue",
        "sizes": ["26", "28", "30", "32"],
    },
    {
        "id": "saree-w-001",
        "name": "Fabindia Silk Saree",
        "description": "Traditional silk saree with border.",
        "price": 4999,
        "currency": "INR",
        "category": "saree",
        "gender": "women",
        "brand": "Fabindia",
        "color": "red",
        "sizes": ["Free Size"],
    },
    # Footwear
    {
        "id": "shoes-m-001",
        "name": "Puma Men's Running Shoes",
        "description": "Lightweight running shoes with cushioning.",
        "price": 3499,
        "currency": "INR",
        "category": "shoes",
        "gender": "men",
        "brand": "Puma",
        "color": "black",
        "sizes": ["7", "8", "9", "10", "11"],
    },
    {
        "id": "shoes-w-001",
        "name": "Bata Women's Heels",
        "description": "Elegant heels for formal occasions.",
        "price": 1999,
        "currency": "INR",
        "category": "shoes",
        "gender": "women",
        "brand": "Bata",
        "color": "nude",
        "sizes": ["5", "6", "7", "8"],
    },
    # Accessories
    {
        "id": "watch-m-001",
        "name": "Fossil Men's Analog Watch",
        "description": "Classic analog watch with leather strap.",
        "price": 8999,
        "currency": "INR",
        "category": "watch",
        "gender": "men",
        "brand": "Fossil",
        "color": "brown",
        "sizes": ["Free Size"],
    },
    {
        "id": "bag-w-001",
        "name": "Caprese Women's Handbag",
        "description": "Stylish handbag for daily use.",
        "price": 1499,
        "currency": "INR",
        "category": "bag",
        "gender": "women",
        "brand": "Caprese",
        "color": "black",
        "sizes": ["Free Size"],
    },
    {
        "id": "belt-m-001",
        "name": "Louis Philippe Leather Belt",
        "description": "Genuine leather belt for formal wear.",
        "price": 999,
        "currency": "INR",
        "category": "belt",
        "gender": "men",
        "brand": "Louis Philippe",
        "color": "black",
        "sizes": ["32", "34", "36", "38"],
    },
    # Kids Wear
    {
        "id": "tee-k-001",
        "name": "H&M Kids T-shirt",
        "description": "Colorful printed t-shirt for kids.",
        "price": 399,
        "currency": "INR",
        "category": "tshirt",
        "gender": "kids",
        "brand": "H&M",
        "color": "yellow",
        "sizes": ["2-3Y", "4-5Y", "6-7Y", "8-9Y"],
    },
    {
        "id": "dress-k-001",
        "name": "Mothercare Girls Dress",
        "description": "Cute dress for special occasions.",
        "price": 899,
        "currency": "INR",
        "category": "dress",
        "gender": "kids",
        "brand": "Mothercare",
        "color": "pink",
        "sizes": ["2-3Y", "4-5Y", "6-7Y"],
    },
]



ORDERS_FILE = "orders.json"

# ensure orders file exists
if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "w") as f:
        json.dump([], f)

# -------------------------
# Per-session Userdata (shopping-centric)
# -------------------------
@dataclass
class Userdata:
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    cart: List[Dict] = field(default_factory=list)  # list of {product_id, quantity, attrs}
    orders: List[Dict] = field(default_factory=list)  # orders placed in this session
    history: List[Dict] = field(default_factory=list)  # conversational actions for trace

# -------------------------
# Merchant-layer helpers (ACP-inspired mini layer)
# -------------------------

def _load_all_orders() -> List[Dict]:
    try:
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_order(order: Dict):
    orders = _load_all_orders()
    orders.append(order)
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, indent=2)


def list_products(filters: Optional[Dict] = None) -> List[Dict]:
    """Naive filtering by category, max_price, color, size substring, or query words.

    Improvements:
    - Accepts category synonyms (e.g., 'phone', 'mobile', 'phones' -> 'mobile').
    - Supports a flexible max_price and min_price (if provided in filters).
    - Matches category by substring if exact match fails.
    """
    filters = filters or {}
    results = []
    query = filters.get("q")
    category = filters.get("category")
    max_price = filters.get("max_price") or filters.get("to") or filters.get("max")
    min_price = filters.get("min_price") or filters.get("from") or filters.get("min")
    color = filters.get("color")
    size = filters.get("size")

    # normalize category synonyms
    if category:
        cat = category.lower()
        if cat in ("phone", "phones", "mobile", "mobile phone", "mobiles"):
            category = "mobile"
        elif cat in ("tshirt", "t-shirts", "tees", "tee"):
            category = "tshirt"
        else:
            category = cat

    for p in CATALOG:
        ok = True
        # category matching: allow substring matches if direct equality fails
        if category:
            pcat = p.get("category", "").lower()
            if pcat != category and category not in pcat and pcat not in category:
                ok = False
        if max_price:
            try:
                if p.get("price", 0) > int(max_price):
                    ok = False
            except Exception:
                pass
        if min_price:
            try:
                if p.get("price", 0) < int(min_price):
                    ok = False
            except Exception:
                pass
        if color and p.get("color") and p.get("color") != color:
            ok = False
        if size and (not p.get("sizes") or size not in p.get("sizes")):
            ok = False
        if query:
            q = query.lower()
            # if query mentions 'phone' or 'mobile', accept mobile category too
            if "phone" in q or "mobile" in q:
                if p.get("category") != "mobile":
                    ok = False
            else:
                if q not in p.get("name", "").lower() and q not in p.get("description", "").lower():
                    ok = False
        if ok:
            results.append(p)
    return results


def find_product_by_ref(ref_text: str, candidates: Optional[List[Dict]] = None) -> Optional[Dict]:
    """Resolve references like 'second hoodie' or 'black hoodie' to a product dict.
    Heuristics improved:
    - Handle ordinals like 'first/second/third' within a filtered candidate list.
    - If ref mentions 'phone' or 'mobile' prefer mobile category products.
    - Match by id, color+category, name substring, or numeric index.
    """
    ref = (ref_text or "").lower().strip()
    cand = candidates if candidates is not None else CATALOG

    # prefer mobiles if user explicitly mentions phone/mobile
    wants_mobile = any(w in ref for w in ("phone", "phones", "mobile", "mobiles"))
    filtered = cand
    if wants_mobile:
        filtered = [p for p in cand if p.get("category") == "mobile"]
        if not filtered:
            filtered = cand

    # ordinal handling
    ordinals = {"first": 0, "second": 1, "third": 2, "fourth": 3}
    for word, idx in ordinals.items():
        if word in ref:
            if idx < len(filtered):
                return filtered[idx]

    # direct id match
    for p in cand:
        if p["id"].lower() == ref:
            return p

    # color + category matching
    for p in cand:
        if p.get("color") and p["color"] in ref and p.get("category") and p["category"] in ref:
            return p

    # name substring or keywords
    for p in filtered:
        name = p["name"].lower()
        if all(tok in name for tok in ref.split() if len(tok) > 2):
            return p
    for p in cand:
        for tok in ref.split():
            if len(tok) > 2 and tok in p["name"].lower():
                return p

    # numeric index like '2' -> second
    for token in ref.split():
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(filtered):
                return filtered[idx]

    # fallback: if user said 'second phone' but we couldn't match earlier, try overall cand ordinals
    for word, idx in ordinals.items():
        if word in ref and idx < len(cand):
            return cand[idx]

    return None


@function_tool
async def show_catalog(
    ctx: RunContext[Userdata],
    q: Annotated[Optional[str], Field(description="Search query (optional)", default=None)] = None,
    category: Annotated[Optional[str], Field(description="Category (optional)", default=None)] = None,
    max_price: Annotated[Optional[int], Field(description="Maximum price (optional)", default=None)] = None,
    color: Annotated[Optional[str], Field(description="Color (optional)", default=None)] = None,
) -> str:
    """Return a short spoken summary of matching products (name, price, id).
    Improvements:
    - Recognize category synonyms like 'phones' and 'tees'.
    - Return up to 8 items and explicitly call out mobiles if present.
    """
    userdata = ctx.userdata
    # try to normalize category input
    if category:
        cat = category.lower()
        if cat in ("phone", "phones", "mobile", "mobile phone", "mobiles"):
            category = "mobile"
        elif cat in ("tshirt", "t-shirts", "tees", "tee"):
            category = "tshirt"
        else:
            category = cat
    # If query mentions phones, prefer category mobile
    if not category and q:
        if any(w in q.lower() for w in ("phone", "phones", "mobile", "mobiles")):
            category = "mobile"
        if any(w in q.lower() for w in ("tee", "tshirt", "t-shirts", "tees")):
            category = "tshirt"

    filters = {"q": q, "category": category, "max_price": max_price, "color": color}
    prods = list_products({k: v for k, v in filters.items() if v is not None})
    if not prods:
        return "Sorry — I couldn't find any items that match. Would you like to try another search?"
    # Summarize top 8
    lines = [f"Here are the top {min(8, len(prods))} items I found at Roshan Shop:"]
    for idx, p in enumerate(prods[:8], start=1):
        size_info = f" (sizes: {', '.join(p['sizes'])})" if p.get('sizes') else ""
        lines.append(f"{idx}. {p['name']} — {p['price']} {p['currency']} (id: {p['id']}){size_info}")
    lines.append("You can say: 'I want the second item in size M' or 'add mug-001 to my cart, quantity 2'.")
    # If mobiles were in results, add a short phrasing hint
    if any(p.get('category') == 'mobile' for p in prods):
        lines.append("To buy a phone say: 'Add phone-002 to my cart' or 'I want the second phone, quantity 1'.")
    return "\n".join(lines)


def find_product_by_ref(ref_text: str, candidates: Optional[List[Dict]] = None) -> Optional[Dict]:
    """Resolve references like 'second hoodie' or 'black hoodie' to a product dict.
    Very simple heuristic: look for ordinal words, color or exact id/name matching.
    """
    ref = (ref_text or "").lower().strip()
    cand = candidates if candidates is not None else CATALOG

    # ordinal handling
    ordinals = {"first": 0, "second": 1, "third": 2}
    for word, idx in ordinals.items():
        if word in ref:
            if idx < len(cand):
                return cand[idx]

    # direct id match
    for p in cand:
        if p["id"].lower() == ref:
            return p

    # color + category matching
    for p in cand:
        if p.get("color") and p["color"] in ref and p.get("category") and p["category"] in ref:
            return p

    # name substring
    for p in cand:
        if p["name"].lower() in ref or any(w in p["name"].lower() for w in ref.split()):
            return p

    # fallback: if a number present, try to parse as '2nd of last list'
    for token in ref.split():
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(cand):
                return cand[idx]

    return None


def create_order_object(line_items: List[Dict], currency: str = "INR") -> Dict:
    """line_items: [{product_id, quantity, attrs}]
    Returns an order dict (id, items, total, currency, created_at)
    """
    items = []
    total = 0
    for li in line_items:
        pid = li.get("product_id")
        qty = int(li.get("quantity", 1))
        prod = next((p for p in CATALOG if p["id"] == pid), None)
        if not prod:
            raise ValueError(f"Product {pid} not found")
        line_total = prod["price"] * qty
        total += line_total
        items.append({
            "product_id": pid,
            "name": prod["name"],
            "unit_price": prod["price"],
            "quantity": qty,
            "line_total": line_total,
            "attrs": li.get("attrs", {}),
        })
    order = {
        "id": f"order-{str(uuid.uuid4())[:8]}",
        "items": items,
        "total": total,
        "currency": currency,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    # persist
    _save_order(order)
    return order


def get_most_recent_order() -> Optional[Dict]:
    all_orders = _load_all_orders()
    if not all_orders:
        return None
    return all_orders[-1]

# -------------------------
# Agent Tools (function_tool) exposed to the LLM layer
# -------------------------

@function_tool
async def show_catalog(
    ctx: RunContext[Userdata],
    q: Annotated[Optional[str], Field(description="Search query (optional)", default=None)] = None,
    category: Annotated[Optional[str], Field(description="Category (optional)", default=None)] = None,
    max_price: Annotated[Optional[int], Field(description="Maximum price (optional)", default=None)] = None,
    color: Annotated[Optional[str], Field(description="Color (optional)", default=None)] = None,
) -> str:
    """Return a short spoken summary of matching products (name, price, id)."""
    userdata = ctx.userdata
    filters = {"q": q, "category": category, "max_price": max_price, "color": color}
    prods = list_products({k: v for k, v in filters.items() if v is not None})
    if not prods:
        return "Sorry — I couldn't find any items that match. Would you like to try another search?"
    # Summarize top 4
    lines = [f"Here are the top {min(4, len(prods))} items I found on Myntra:"]
    for idx, p in enumerate(prods[:4], start=1):
        lines.append(f"{idx}. {p['name']} — {p['price']} {p['currency']} (id: {p['id']})")
    lines.append("You can say: 'I want the second item in size M' or 'add mug-001 to my cart, quantity 2'.")
    return "\n".join(lines)


@function_tool
async def add_to_cart(
    ctx: RunContext[Userdata],
    product_ref: Annotated[str, Field(description="Reference to product: id, name, or spoken ref")] ,
    quantity: Annotated[int, Field(description="Quantity", default=1)] = 1,
    size: Annotated[Optional[str], Field(description="Size (optional)", default=None)] = None,
) -> str:
    """Resolve a product and add to the session cart."""
    userdata = ctx.userdata
    # take recent catalog as candidates
    candidates = CATALOG
    prod = find_product_by_ref(product_ref, candidates)
    if not prod:
        return "I couldn't resolve which product you meant. Try using the item id or say 'show catalog' to hear options.'"
    userdata.cart.append({
        "product_id": prod["id"],
        "quantity": int(quantity),
        "attrs": {"size": size} if size else {},
    })
    userdata.history.append({
        "time": datetime.utcnow().isoformat() + "Z",
        "action": "add_to_cart",
        "product_id": prod["id"],
        "quantity": int(quantity),
    })
    return f"Added {quantity} x {prod['name']} to your cart. What would you like to do next?"


@function_tool
async def show_cart(
    ctx: RunContext[Userdata],
) -> str:
    userdata = ctx.userdata
    if not userdata.cart:
        return "Your cart is empty. You can say 'show catalog' to browse items.'"
    lines = ["Items in your cart:"]
    total = 0
    for li in userdata.cart:
        p = next((x for x in CATALOG if x["id"] == li["product_id"]), None)
        if not p:
            continue
        line_total = p["price"] * li.get("quantity", 1)
        total += line_total
        sz = li.get("attrs", {}).get("size")
        sz_text = f", size {sz}" if sz else ""
        lines.append(f"- {p['name']} x {li['quantity']}{sz_text}: {line_total} INR")
    lines.append(f"Cart total: {total} INR")
    lines.append("Say 'place my order' to checkout or 'clear cart' to empty the cart.")
    return "\n".join(lines)


@function_tool
async def clear_cart(
    ctx: RunContext[Userdata],
) -> str:
    userdata = ctx.userdata
    userdata.cart = []
    userdata.history.append({"time": datetime.utcnow().isoformat() + "Z", "action": "clear_cart"})
    return "Your cart has been cleared. What would you like to do next?"


@function_tool
async def save_delivery_details(
    ctx: RunContext[Userdata],
    name: Annotated[str, Field(description="Customer name")],
    phone: Annotated[str, Field(description="Phone number")],
    address: Annotated[str, Field(description="Delivery address")],
    pincode: Annotated[str, Field(description="PIN code")],
) -> str:
    """Save customer delivery details before checkout."""
    userdata = ctx.userdata
    userdata.customer_name = name
    userdata.phone = phone
    userdata.address = address
    userdata.pincode = pincode
    userdata.history.append({
        "time": datetime.utcnow().isoformat() + "Z",
        "action": "save_delivery_details",
        "name": name,
    })
    return f"Delivery details saved for {name}. Phone: {phone}, PIN: {pincode}. Ready to place your order?"


@function_tool
async def place_order(
    ctx: RunContext[Userdata],
    confirm: Annotated[bool, Field(description="Confirm order placement", default=True)] = True,
) -> str:
    """Create order from session cart and persist. Returns order summary."""
    userdata = ctx.userdata
    if not userdata.cart:
        return "Your cart is empty — nothing to place. Would you like to browse items?"
    
    # Check if delivery details are provided
    if not userdata.customer_name or not userdata.phone or not userdata.address or not userdata.pincode:
        missing = []
        if not userdata.customer_name:
            missing.append("name")
        if not userdata.phone:
            missing.append("phone number")
        if not userdata.address:
            missing.append("delivery address")
        if not userdata.pincode:
            missing.append("PIN code")
        return f"Before placing your order, I need your {', '.join(missing)}. Please provide these details."
    
    # Build line_items
    line_items = []
    for li in userdata.cart:
        line_items.append({
            "product_id": li["product_id"],
            "quantity": li.get("quantity", 1),
            "attrs": li.get("attrs", {}),
        })
    order = create_order_object(line_items)
    
    # Add delivery details to order
    order["customer_name"] = userdata.customer_name
    order["phone"] = userdata.phone
    order["address"] = userdata.address
    order["pincode"] = userdata.pincode
    
    userdata.orders.append(order)
    userdata.history.append({"time": datetime.utcnow().isoformat() + "Z", "action": "place_order", "order_id": order["id"]})
    
    # clear cart after order
    userdata.cart = []
    
    return f"Order placed successfully! Order ID: {order['id']}. Total: ₹{order['total']}. Your order will be delivered to {userdata.address}, PIN: {userdata.pincode}. Expected delivery in 3-5 business days. What would you like to do next?"


@function_tool
async def last_order(
    ctx: RunContext[Userdata],
) -> str:
    ord = get_most_recent_order()
    if not ord:
        return "You have no past orders yet."
    lines = [f"Most recent order: {ord['id']} — {ord['created_at']}"]
    for it in ord['items']:
        lines.append(f"- {it['name']} x {it['quantity']}: {it['line_total']} {ord['currency']}")
    lines.append(f"Total: {ord['total']} {ord['currency']}")
    return "\n".join(lines)

# -------------------------
# The Agent (Ramu Kaka)
# -------------------------
class MyntraShoppingAgent(Agent):
    def __init__(self):
        # System instructions for Myntra fashion shopping assistant
        instructions = """
        You are 'Maya', the friendly AI shopping assistant for Myntra - India's leading fashion e-commerce platform.
        Universe: Online fashion marketplace with trending brands like Nike, Levi's, H&M, Zara, Roadster, Libas, and more.
        Tone: Trendy, helpful, fashion-forward; keep sentences short for voice clarity.
        Role: Help customers discover fashion, browse by brand/category/gender, add items to cart, and place orders.

        Rules:
            - Use the provided tools to show catalog, add items to cart, show cart, place orders, show last order, and clear cart.
            - Mention brand names when presenting products (e.g., "Nike Sportswear Hoodie").
            - Help with size selection - ask if they need help with sizing.
            - Keep continuity using per-session userdata. Mention cart contents if relevant.
            - Drive short voice-first turns suitable for spoken delivery.
            - When presenting options, include brand, product name, and price (e.g., 'Roadster Graphic Tee — ₹499').
            - Suggest complementary items when appropriate (e.g., "Would you like to see matching jeans?").
            - IMPORTANT: Before placing an order, ALWAYS collect delivery details using save_delivery_details tool:
              * Customer name
              * Phone number (10 digits)
              * Complete delivery address
              * PIN code (6 digits)
            - Ask for delivery details naturally: "To complete your order, I'll need your name, phone number, delivery address, and PIN code."
            - After saving delivery details, confirm them back to the customer before placing the order.
        """
        super().__init__(
            instructions=instructions,
            tools=[show_catalog, add_to_cart, show_cart, clear_cart, save_delivery_details, place_order, last_order],
        )

# -------------------------
# Entrypoint & Prewarm (keeps speech functionality untouched)
# -------------------------
def prewarm(proc: JobProcess):
    # load VAD model and stash on process userdata, try/catch like original file
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        logger.warning("VAD prewarm failed; continuing without preloaded VAD.")


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info("\n" + "🛍️" * 6)
    logger.info("🚀 STARTING MYNTRA VOICE SHOPPING ASSISTANT — Maya")

    userdata = Userdata()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-alicia",
            style="Conversational",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata.get("vad"),
        userdata=userdata,
    )

    # Start the agent session with the MyntraShoppingAgent (Maya)
    await session.start(
        agent=MyntraShoppingAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))