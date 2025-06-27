from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# Import our modules
from src.database.connection import database, create_tables, get_database
from src.database.repository import OrderRepository
from src.services.eventhub import EventHubService
from src.services.order_service import OrderService
from src.schemas.order import OrderRequest, OrderResponse

# Create FastAPI app
app = FastAPI(
    title="Order Service", 
    version="1.0.0",
    description="Event-driven order processing microservice"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
eventhub_service = EventHubService()

# Dependency to get order service
async def get_order_service() -> OrderService:
    db = await get_database()
    order_repository = OrderRepository(db)
    return OrderService(order_repository, eventhub_service)

# Database connection events
@app.on_event("startup")
async def startup():
    create_tables()
    await database.connect()
    print("Database connected and tables created")

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    print("Database disconnected")

# Health endpoints
@app.get("/")
async def root():
    return {
        "message": "Order Service API", 
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "order-service",
        "database": "connected",
        "eventhub": "configured" if eventhub_service.connection_string else "not_configured"
    }

# Order endpoints
@app.post("/api/orders", response_model=OrderResponse)
async def create_order(
    order_request: OrderRequest, 
    order_service: OrderService = Depends(get_order_service)
):
    """Create a new order"""
    try:
        order = await order_service.create_order(order_request)
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating order: {str(e)}")

@app.get("/api/orders", response_model=List[OrderResponse])
async def get_all_orders(order_service: OrderService = Depends(get_order_service)):
    """Get all orders"""
    try:
        orders = await order_service.get_all_orders()
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching orders: {str(e)}")

@app.get("/api/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str, 
    order_service: OrderService = Depends(get_order_service)
):
    """Get a specific order by ID"""
    try:
        order = await order_service.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching order: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
