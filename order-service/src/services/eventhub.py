import json
import os
from azure.eventhub.aio import EventHubProducerClient
from azure.eventhub import EventData
from src.schemas.order import OrderResponse

class EventHubService:
    def __init__(self):
        self.connection_string = os.getenv("EVENTHUB_CONNECTION_STRING")
        self.eventhub_name = "orders"
        
        if not self.connection_string:
            print("Warning: EVENTHUB_CONNECTION_STRING not set")
    
    async def send_order_event(self, order: OrderResponse) -> bool:
        """Send order event to Azure Event Hub"""
        if not self.connection_string:
            print("Skipping event send - no connection string")
            return False
            
        try:
            async with EventHubProducerClient.from_connection_string(
                self.connection_string, 
                eventhub_name=self.eventhub_name
            ) as producer:
                # Create event data
                order_dict = {
                    "id": order.id,
                    "customer_id": order.customer_id,
                    "product_id": order.product_id,
                    "quantity": order.quantity,
                    "price": order.price,
                    "created_at": order.created_at.isoformat(),
                    "status": order.status,
                    "event_type": "order_created",
                    "timestamp": order.created_at.isoformat()
                }
                
                event_data = EventData(json.dumps(order_dict))
                await producer.send_batch([event_data])
                print(f"Order event sent: {order.id}")
                return True
                
        except Exception as e:
            print(f"Error sending event: {e}")
            return False
    
    async def send_custom_event(self, event_type: str, data: dict) -> bool:
        """Send custom event to Event Hub"""
        if not self.connection_string:
            print("Skipping event send - no connection string")
            return False
            
        try:
            async with EventHubProducerClient.from_connection_string(
                self.connection_string, 
                eventhub_name=self.eventhub_name
            ) as producer:
                event_data = EventData(json.dumps({
                    "event_type": event_type,
                    "data": data,
                    "timestamp": data.get("timestamp", "")
                }))
                
                await producer.send_batch([event_data])
                print(f"Custom event sent: {event_type}")
                return True
                
        except Exception as e:
            print(f"Error sending custom event: {e}")
            return False