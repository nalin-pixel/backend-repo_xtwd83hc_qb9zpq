import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import db, create_document, get_documents
from schemas import Product, Review, Bundle, SparePart, Brand, Category, SearchSuggestion, Order

app = FastAPI(title="ThePowerSite Replacement API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "service": "backend", "name": "ThePowerSite API"}

# Seed demo data if empty
@app.on_event("startup")
async def seed_data():
    if db is None:
        return
    # Only seed if no products exist
    if not db["product"].find_one({}):
        demo_brand_hyundai = {
            "name": "Hyundai Power Products",
            "slug": "hyundai",
            "color": "#1e40af",
            "logo_url": "https://upload.wikimedia.org/wikipedia/commons/2/27/Hyundai_logo.svg",
        }
        demo_brand_jcb = {
            "name": "JCB Tools",
            "slug": "jcb",
            "color": "#ffcc00",
            "logo_url": "https://upload.wikimedia.org/wikipedia/commons/8/8e/JCB_logo.svg",
        }
        for b in [demo_brand_hyundai, demo_brand_jcb]:
            db["brand"].update_one({"slug": b["slug"]}, {"$set": b}, upsert=True)

        categories = [
            {"name": "Generators", "slug": "generators", "parent_slug": None},
            {"name": "Pressure Washers", "slug": "pressure-washers", "parent_slug": None},
            {"name": "Chainsaws", "slug": "chainsaws", "parent_slug": None},
        ]
        for c in categories:
            db["category"].update_one({"slug": c["slug"]}, {"$set": c}, upsert=True)

        products = [
            {
                "sku": "HY2000i",
                "title": "Hyundai 2000W Inverter Generator",
                "short_bullets": [
                    "2000W peak power",
                    "Super-quiet 58dB",
                    "Lightweight 21kg",
                ],
                "brand": "hyundai",
                "category": "generators",
                "power_source": "petrol",
                "capacity": "2kW",
                "weight_kg": 21.0,
                "price": {"inc_vat": 599.99, "ex_vat": 499.99, "currency": "GBP", "finance_available": True},
                "media": {
                    "images": [
                        "https://images.unsplash.com/photo-1547234935-80c7145ec969?w=900",
                    ],
                    "video_url": None,
                },
                "specs": [
                    {"label": "Output", "value": "2000W peak / 1600W rated"},
                    {"label": "Noise", "value": "58dB @ 7m"},
                ],
                "rating_avg": 4.6,
                "rating_count": 124,
                "accessories": ["HYCABLE1"],
                "related_skus": ["HY3000i"],
                "stock": 12,
            },
            {
                "sku": "JCB-18V-IMPACT",
                "title": "JCB 18V Brushless Impact Driver",
                "short_bullets": [
                    "High-torque brushless motor",
                    "Compact body for tight spaces",
                    "LED work light",
                ],
                "brand": "jcb",
                "category": "chainsaws",
                "power_source": "battery",
                "capacity": "18V",
                "weight_kg": 1.4,
                "price": {"inc_vat": 129.99, "ex_vat": 108.33, "currency": "GBP", "finance_available": False},
                "media": {
                    "images": [
                        "https://images.unsplash.com/photo-1581093588401-16ec5a7b1d86?w=900",
                    ],
                },
                "specs": [
                    {"label": "Chuck", "value": "1/4"},
                    {"label": "Max Torque", "value": "180Nm"},
                ],
                "rating_avg": 4.4,
                "rating_count": 54,
                "accessories": ["JCB-18V-BAT", "JCB-FAST-CHARGER"],
                "related_skus": ["JCB-18V-DRILL"],
                "stock": 30,
            },
        ]
        db["product"].insert_many(products)


# Schemas endpoint to expose collection models to the DB viewer
@app.get("/schema")
def schema_info():
    from schemas import __dict__ as mod
    keys = [k for k, v in mod.items() if isinstance(v, type) and issubclass(v, BaseModel)]
    return {"models": keys}

# Search with suggestions (autocomplete)
@app.get("/api/search", response_model=List[SearchSuggestion])
def search(q: str = Query(..., min_length=1, max_length=60), limit: int = 8):
    if db is None:
        return []
    cursor = db["product"].find({"title": {"$regex": q, "$options": "i"}}).limit(limit)
    out: List[SearchSuggestion] = []
    for p in cursor:
        out.append(
            SearchSuggestion(
                sku=p["sku"],
                title=p["title"],
                brand=p["brand"],
                category=p["category"],
                price_inc_vat=p["price"]["inc_vat"],
                image=(p.get("media", {}).get("images", [None]) or [None])[0],
            )
        )
    return out

# Catalog endpoints
@app.get("/api/brands")
def get_brands():
    return list(db["brand"].find({}, {"_id": 0})) if db else []

@app.get("/api/categories")
def get_categories():
    return list(db["category"].find({}, {"_id": 0})) if db else []

@app.get("/api/products")
def list_products(
    brand: Optional[str] = None,
    category: Optional[str] = None,
    power_source: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    page_size: int = 12,
):
    if db is None:
        return {"items": [], "total": 0}
    query = {}
    if brand:
        query["brand"] = brand
    if category:
        query["category"] = category
    if power_source:
        query["power_source"] = power_source
    if min_price is not None or max_price is not None:
        query["price.inc_vat"] = {}
        if min_price is not None:
            query["price.inc_vat"]["$gte"] = min_price
        if max_price is not None:
            query["price.inc_vat"]["$lte"] = max_price

    total = db["product"].count_documents(query)
    items = list(
        db["product"].find(query, {"_id": 0})
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@app.get("/api/products/{sku}")
def get_product(sku: str):
    if db is None:
        raise HTTPException(500, "Database unavailable")
    p = db["product"].find_one({"sku": sku}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Product not found")
    # Attach accessories and related products summaries
    if p.get("accessories"):
        acc = list(db["product"].find({"sku": {"$in": p["accessories"]}}, {"_id": 0, "sku": 1, "title": 1, "price": 1, "media": 1}))
        p["accessory_items"] = acc
    if p.get("related_skus"):
        rel = list(db["product"].find({"sku": {"$in": p["related_skus"]}}, {"_id": 0, "sku": 1, "title": 1, "price": 1, "media": 1}))
        p["related_items"] = rel
    return p

# Reviews (Amazon-style, most recent first)
@app.get("/api/products/{sku}/reviews")
def get_reviews(sku: str, page: int = 1, page_size: int = 10):
    if db is None:
        return {"items": [], "total": 0}
    query = {"sku": sku}
    total = db["review"].count_documents(query)
    items = list(
        db["review"].find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    )
    return {"items": items, "total": total}

@app.post("/api/products/{sku}/reviews")
def post_review(sku: str, review: Review):
    if db is None:
        raise HTTPException(500, "Database unavailable")
    if not db["product"].find_one({"sku": sku}):
        raise HTTPException(404, "Product not found")
    review_dict = review.model_dump()
    review_dict["sku"] = sku
    create_document("review", review_dict)
    return {"status": "ok"}

# Checkout demo
@app.post("/api/checkout")
def checkout(order: Order):
    if db is None:
        raise HTTPException(500, "Database unavailable")
    oid = create_document("order", order)
    return {"status": "ok", "order_id": oid}

# Spare parts simple search
@app.get("/api/spares")
def spares_for(sku: Optional[str] = None, q: Optional[str] = None):
    if db is None:
        return []
    query = {}
    if sku:
        query["compatible_skus"] = sku
    if q:
        query["title"] = {"$regex": q, "$options": "i"}
    return list(db["sparepart"].find(query, {"_id": 0}))

# Health & DB test
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available" if db is None else "✅ Connected",
    }
    try:
        if db is not None:
            response["collections"] = db.list_collection_names()
    except Exception as e:
        response["database"] = f"Error: {str(e)[:60]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
