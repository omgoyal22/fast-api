from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
from pymongo import MongoClient
from bson import ObjectId

# FastAPI app
app = FastAPI()

# MongoDB connection
client = MongoClient("mongodb+srv://omeesolution:omg123@cluster0.g8nd8em.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.notes
products_collection = db.products
orders_collection = db.orders

# Data Models
class Size(BaseModel):
    size: str
    quantity: int

class ProductCreate(BaseModel):
    name: str
    price: float
    sizes: List[Size]

class ProductOut(BaseModel):
    id: str
    name: str
    price: float

class Pagination(BaseModel):
    next: int
    limit: int
    previous: int

class ProductListResponse(BaseModel):
    data: List[ProductOut]
    page: Pagination

class OrderItem(BaseModel):
    productId: str
    qty: int

class OrderCreate(BaseModel):
    userId: str
    items: List[OrderItem]

class IDResponse(BaseModel):
    id: str


# API: Create Product

@app.post("/products", response_model=IDResponse, status_code=201)
def create_product(product: ProductCreate):
    product_id = str(uuid4())
    product_dict = {"_id": product_id, **product.dict()}
    products_collection.insert_one(product_dict)
    return {"id": product_id}

# API: List Products
@app.get("/products", response_model=ProductListResponse)
def list_products(
    name: Optional[str] = None,
    size: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
):
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if size:
        query["sizes.size"] = size

    cursor = products_collection.find(query).skip(offset).limit(limit)
    data = [
        {"id": doc["_id"], "name": doc["name"], "price": doc["price"]}
        for doc in cursor
    ]

    return {
        "data": data,
        "page": {
            "next": offset + limit,
            "limit": len(data),
            "previous": offset - limit
        }
    }

# API: Create Order
@app.post("/orders", response_model=IDResponse, status_code=201)
def create_order(order: OrderCreate):
    order_id = str(uuid4())
    order_dict = {"_id": order_id, **order.dict()}
    orders_collection.insert_one(order_dict)
    return {"id": order_id}


# NEW: API: List Orders by User with Product Lookup
@app.get("/orders/{user_id}")
def list_orders(
    user_id: str,
    limit: int = 10,
    offset: int = 0
):
    query = {"userId": user_id}
    cursor = orders_collection.find(query).skip(offset).limit(limit)
    data = []

    for order in cursor:
        order_items = []
        total = 0.0

        for item in order["items"]:
            product = products_collection.find_one({"_id": item["productId"]})
            if product:
                product_detail = {
                    "id": product["_id"],
                    "name": product["name"]
                }
                subtotal = item["qty"] * product["price"]
                total += subtotal
            else:
                product_detail = {"id": item["productId"], "name": "Unknown"}

            order_items.append({
                "productDetails": product_detail,
                "qty": item["qty"]
            })

        data.append({
            "id": order["_id"],
            "items": order_items,
            "total": round(total, 2)
        })

    return {
        "data": data,
        "page": {
            "next": offset + limit,
            "limit": len(data),
            "previous": offset - limit
        }
    }
