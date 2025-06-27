from pydantic import BaseModel
from datetime import datetime

class OrderRequest(BaseModel):
    customer_id: str
    product_id: str
    quantity: int
    price: float

class OrderResponse(BaseModel):
    id: str
    customer_id: str
    product_id: str
    quantity: int
    price: float
    created_at: datetime
    status: str

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    id: str
    customer_id: str
    product_id: str
    quantity: int
    price: float
    created_at: datetime
    status: str = "PENDING"