import uuid
from datetime import datetime
from typing import List, Optional
import asyncio

from src.schemas.order import OrderRequest, OrderResponse, OrderCreate
from src.database.repository import OrderRepository
from src.services.eventhub import EventHubService

class OrderService:
    def __init__(self, order_repository: OrderRepository, eventhub_service: EventHubService):
        self.order_repository = order_repository
        self.eventhub_service = eventhub_service
    
    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        """Create a new order and send event"""
        # Generate order data
        order_create = OrderCreate(
            id=str(uuid.uuid4()),
            customer_id=order_request.customer_id,
            product_id=order_request.product_id,
            quantity=order_request.quantity,
            price=order_request.price,
            created_at=datetime.utcnow(),
            status="PENDING"
        )
        
        # Save to database
        order = await self.order_repository.create_order(order_create)
        
        # Send event to Event Hub (async, non-blocking)
        asyncio.create_task(self.eventhub_service.send_order_event(order))
        
        return order
    
    async def get_all_orders(self) -> List[OrderResponse]:
        """Get all orders"""
        return await self.order_repository.get_all_orders()
    
    async def get_order_by_id(self, order_id: str) -> Optional[OrderResponse]:
        """Get order by ID"""
        return await self.order_repository.get_order_by_id(order_id)
    
    async def update_order_status(self, order_id: str, status: str) -> Optional[OrderResponse]:
        """Update order status and send event"""
        # This is a placeholder for future implementation
        # Would typically update database and send status change event
        pass