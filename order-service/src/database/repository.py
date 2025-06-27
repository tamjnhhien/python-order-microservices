from typing import List, Optional
from databases import Database
from src.schemas.order import OrderCreate, OrderResponse

class OrderRepository:
    def __init__(self, database: Database):
        self.database = database
    
    async def create_order(self, order: OrderCreate) -> OrderResponse:
        """Create a new order in the database"""
        query = """
            INSERT INTO orders (id, customer_id, product_id, quantity, price, created_at, status)
            VALUES (:id, :customer_id, :product_id, :quantity, :price, :created_at, :status)
        """
        
        values = {
            "id": order.id,
            "customer_id": order.customer_id,
            "product_id": order.product_id,
            "quantity": order.quantity,
            "price": order.price,
            "created_at": order.created_at,
            "status": order.status
        }
        
        await self.database.execute(query=query, values=values)
        return OrderResponse(**order.dict())
    
    async def get_all_orders(self) -> List[OrderResponse]:
        """Get all orders from the database"""
        query = "SELECT * FROM orders ORDER BY created_at DESC"
        orders = await self.database.fetch_all(query=query)
        return [OrderResponse(**dict(order)) for order in orders]
    
    async def get_order_by_id(self, order_id: str) -> Optional[OrderResponse]:
        """Get a specific order by ID"""
        query = "SELECT * FROM orders WHERE id = :order_id"
        order = await self.database.fetch_one(query=query, values={"order_id": order_id})
        
        if not order:
            return None
        
        return OrderResponse(**dict(order))