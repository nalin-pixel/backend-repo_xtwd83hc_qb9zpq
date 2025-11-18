"""
Database Schemas for ThePowerSite replacement demo

Each Pydantic model maps to a MongoDB collection using the lowercase
class name as the collection name.
"""
from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, HttpUrl

# Core catalog entities
class Brand(BaseModel):
    name: str = Field(..., description="Brand display name, e.g., Hyundai")
    slug: str = Field(..., description="URL-safe slug, e.g., hyundai")
    color: Optional[str] = Field(None, description="Hex color for brand accents")
    logo_url: Optional[HttpUrl] = None

class Category(BaseModel):
    name: str
    slug: str
    parent_slug: Optional[str] = Field(None, description="Parent category slug for hierarchy")
    image_url: Optional[HttpUrl] = None

PowerSource = Literal["petrol", "diesel", "electric", "battery", "corded", "air", "manual"]

class PriceInfo(BaseModel):
    inc_vat: float = Field(..., ge=0)
    ex_vat: float = Field(..., ge=0)
    currency: Literal["GBP"] = "GBP"
    finance_available: bool = True

class Media(BaseModel):
    images: List[HttpUrl] = []
    video_url: Optional[HttpUrl] = None
    spin_360_url: Optional[HttpUrl] = None

class SpecItem(BaseModel):
    label: str
    value: str

class Product(BaseModel):
    sku: str
    title: str
    short_bullets: List[str] = []
    description: Optional[str] = None
    brand: str = Field(..., description="Brand slug")
    category: str = Field(..., description="Category slug")
    power_source: Optional[PowerSource] = None
    capacity: Optional[str] = None
    size: Optional[str] = None
    weight_kg: Optional[float] = Field(None, ge=0)
    application: Optional[List[str]] = None
    price: PriceInfo
    media: Media = Media()
    specs: List[SpecItem] = []
    rating_avg: float = 0
    rating_count: int = 0
    accessories: List[str] = Field(default_factory=list, description="SKU list of accessories")
    related_skus: List[str] = Field(default_factory=list)
    stock: int = 10

class Review(BaseModel):
    sku: str
    title: str
    body: str
    rating: int = Field(..., ge=1, le=5)
    author: str

class Bundle(BaseModel):
    sku: str
    title: str
    items: List[str] = Field(default_factory=list, description="SKUs included")
    price: PriceInfo

class SparePart(BaseModel):
    sku: str
    title: str
    compatible_skus: List[str] = []
    price: PriceInfo

class Address(BaseModel):
    full_name: str
    line1: str
    line2: Optional[str] = None
    city: str
    county: Optional[str] = None
    postcode: str
    country: str = "UK"

class OrderItem(BaseModel):
    sku: str
    title: str
    qty: int = Field(..., ge=1)
    unit_price_inc_vat: float

class Order(BaseModel):
    email: str
    phone: Optional[str] = None
    shipping_address: Address
    billing_address: Optional[Address] = None
    items: List[OrderItem]
    total_inc_vat: float
    payment_method: Literal["card", "apple_pay", "google_pay", "cod"] = "card"

# Simple response shapes
class SearchSuggestion(BaseModel):
    sku: str
    title: str
    brand: str
    category: str
    price_inc_vat: float
    image: Optional[HttpUrl] = None

# Optional: lightweight user for dashboard demo
class User(BaseModel):
    name: str
    email: str
    address: Optional[str] = None
    is_active: bool = True
