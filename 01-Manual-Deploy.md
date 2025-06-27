# Session 1: Build Python Order Microservice + Azure Event Hub

## What You'll Build Today (2 minutes)
**End Result:** A live Python microservice with clean architecture running on Azure App Service that processes orders and sends real-time events - deployed using your preferred method.

---

## Hands-On Block (58 minutes)
### Step 1: Create Python Order Service
On your local machine:

**Create requirements.txt:**
- Windows: PowerShell
  ```powershell
  @"
  # Python dependencies for Order Service
  fastapi==0.104.1
  uvicorn[standard]==0.24.0
  httpx==0.25.2
  flake8==6.1.0
  pydantic==2.5.0
  azure-eventhub==5.11.4
  azure-identity==1.15.0
  sqlalchemy==2.0.23
  aiosqlite==0.19.0
  python-multipart==0.0.6
  python-json-logger==2.0.7
  databases[sqlite]>=0.9.0
  "@ | Set-Content requirements.txt
  ```
- Linux/Mac: bash
  ```txt
  cat > requirements.txt << EOF
  # Python dependencies for Order Service
  fastapi==0.104.1
  uvicorn[standard]==0.24.0
  httpx==0.25.2
  flake8==6.1.0
  pydantic==2.5.0
  azure-eventhub==5.11.4
  azure-identity==1.15.0
  sqlalchemy==2.0.23
  aiosqlite==0.19.0
  python-multipart==0.0.6
  python-json-logger==2.0.7
  databases[sqlite]>=0.9.0
  EOF
  ```

**Create project directory structure:**
```
current_workspace
├── order-service/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── order.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── order.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── eventhub.py
│   │   │   └── order_service.py
│   │   └── database/
│   │       ├── __init__.py
│   │       ├── connection.py
│   │       └── repository.py
│   └── main.py
├── requirements.txt
├── .gitignore
├── orders.db
└── README.md
```

```bash
mkdir order-service
cd order-service
mkdir -p src/{models,schemas,services,database}
touch src/__init__.py
touch src/models/__init__.py
touch src/schemas/__init__.py
touch src/services/__init__.py
touch src/database/__init__.py
```

```powershell
New-Item -ItemType Directory -Path "order-service"
Set-Location "order-service"
New-Item -ItemType Directory -Path "src\models","src\schemas","src\services","src\database"
New-Item -ItemType File -Path "src\__init__.py"
New-Item -ItemType File -Path "src\models\__init__.py"
New-Item -ItemType File -Path "src\schemas\__init__.py"
New-Item -ItemType File -Path "src\services\__init__.py"
New-Item -ItemType File -Path "src\database\__init__.py"
```

**Create Database Models (`src/models/order.py`):**
```python
from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class OrderDB(Base):
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    product_id = Column(String, index=True)
    quantity = Column(Integer)
    price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="PENDING")
```

**Create Pydantic Schemas (`src/schemas/order.py`):**
```python
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
```

**Create Database Repository (`src/database/repository.py`):**
```python
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
```

**Create Database Service (`src/database/connection.py`):**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from databases import Database
from src.models.order import Base

DATABASE_URL = "sqlite:///./orders.db"

# Async database connection
database = Database(DATABASE_URL)

# Sync database connection for table creation
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)

async def get_database():
    """Get database connection"""
    return database
```

**Create Event Hub Service (`src/services/eventhub.py`):**
```python
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
```

**Create Order Service (`src/services/order_service.py`):**
```python
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
```

**Create Main Application (`main.py`):**
```python
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
```

```bash
# Run locally
cd .\order-service\ ; python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 2: Setup Azure Environment
Go to Azure Cloud Shell
Use Bash (No network + Select existing RG)
```bash
# Variables for your resources
RG=
LOCATION=eastus
APP_NAME="orders-api-$(date +%s)"
APP_SERVICE_PLAN="plan-ecommerce"
EVENTHUB_NAMESPACE="events-ns-$(date +%s)"
EVENTHUB_NAME="orders"

# Create App Service Plan (REQUIRED FIRST!)
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RG \
  --location $LOCATION \
  --sku B3 \
  --is-linux

# Create Event Hub namespace and hub
az eventhubs namespace create \
  --name $EVENTHUB_NAMESPACE \
  --resource-group $RG \
  --sku Standard \
  --location $LOCATION

az eventhubs eventhub create \
  --name $EVENTHUB_NAME \
  --namespace-name $EVENTHUB_NAMESPACE \
  --resource-group $RG \
  --partition-count 1

# Get connection string (save this!)
EVENTHUB_CONNECTION_STRING=$(az eventhubs namespace authorization-rule keys list \
  --resource-group $RG \
  --namespace-name $EVENTHUB_NAMESPACE \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString --output tsv)

echo "Event Hub Connection String: $EVENTHUB_CONNECTION_STRING"
```

Submission: screenshot of the Azure Portal showing:
- App Service Plan created
- Event Hub Namespace and Event Hub created


### Step 3: Deployment to App Service

### 3A. Setup Azure DevOps Repository

Make sure you make the projecct public or use a personal access token (PAT) for private repos if it is GitHub private repo.

```bash
# Get repository URL
DEVOPS_REPO_URL=https://trietvominh1997@dev.azure.com/trietvominh1997/Self-Learning/_git/Self-Learning # e.g https://dev.azure.com/qwewqewr/ecommerce-microservices/_git/order-service
REPO_BRANCH=main
echo "Repository URL: $DEVOPS_REPO_URL"

```

### 3B. Deploy using Azure Cloud Shell

# Create the Web App with Azure DevOps deployment using Azure Cloud Shell
```bash
az webapp list-runtimes --os linux --output table

az webapp create \
  --name $APP_NAME \
  --resource-group $RG \
  --plan $APP_SERVICE_PLAN \
  --runtime "PYTHON:3.9" \
  --deployment-source-url $DEVOPS_REPO_URL \
  --deployment-source-branch $REPO_BRANCH

az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RG \
  --settings EVENTHUB_CONNECTION_STRING="$EVENTHUB_CONNECTION_STRING"

# Configure startup command
az webapp config set \
  --name $APP_NAME \
  --resource-group $RG \
  --startup-file "uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir d1/order-service"

# Get the app URL
APP_URL=$(az webapp show --name $APP_NAME --resource-group $RG --query defaultHostName --output tsv)
echo "Your API is live at: https://$APP_URL"
```

---

## Step 4: Test Your Live API (5 minutes)

**Test commands (same for all deployment methods):**

```bash
# Wait for app to start
sleep 30

# Test health endpoint
curl https://$APP_URL/health

# Test root endpoint
curl https://$APP_URL/

# Test creating an order
curl -X POST https://$APP_URL/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-123",
    "product_id": "laptop-pro",
    "quantity": 1,
    "price": 1299.99
  }'

# Get all orders
curl https://$APP_URL/api/orders

# Test another order
curl -X POST https://$APP_URL/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-456", 
    "product_id": "wireless-mouse",
    "quantity": 2,
    "price": 29.99
  }'
```

## Step 5: Verify and Monitor (5 minutes)

```bash
# Check App Service Plan details
az appservice plan show \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --query "{name:name, sku:sku.name, location:location}"

# Check Event Hub metrics
az eventhubs eventhub show \
  --resource-group $RESOURCE_GROUP \
  --namespace-name $EVENTHUB_NAMESPACE \
  --name orders \
  --query "{name:name, partitionCount:partitionCount, status:status}"

# View application logs
az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP

# Test API documentation (FastAPI auto-generates this)
echo "API Documentation available at: https://$APP_URL/docs"

# Show final resource summary
echo "=== Your Resources ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "App Service Plan: $APP_SERVICE_PLAN (B1 SKU)"
echo "Web App: $APP_NAME"
echo "API URL: https://$APP_URL/api/orders"
echo "API Docs: https://$APP_URL/docs"
echo "Event Hub Namespace: $EVENTHUB_NAMESPACE"
echo "Event Hub: orders"
```

---

## What You Built Today:

✅ **Clean Architecture** - Properly separated concerns with repository pattern  
✅ **Multiple Deployment Options** - GitHub, Azure DevOps, and Local deployment  
✅ **Live Python API** - Running at `https://your-app.azurewebsites.net`  
✅ **Event-Driven Architecture** - Orders automatically send events to Event Hub  
✅ **Professional Code Structure** - Industry-standard Python project organization  
✅ **FastAPI with Auto-Documentation** - Interactive API docs at `/docs`  
✅ **Production Ready** - Health checks, error handling, and monitoring  

## Deployment Methods Comparison:

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **GitHub + Azure Cloud Shell** | Open source projects, public repos | Easy CI/CD setup, version control integration | Requires public repo or GitHub Actions |
| **Azure DevOps + Azure Cloud Shell** | Enterprise projects, private repos | Full DevOps integration, private repos | More complex setup, Azure DevOps learning curve |
| **Local + Azure CLI** | Quick deployment, development | Simple, direct control | Manual process, no automatic CI/CD |

## Session Recap:

### Key Takeaways:
1. **Clean Architecture** - Built modular, maintainable code structure
2. **Multiple Deployment Strategies** - Learned 3 different deployment approaches
3. **Repository Pattern** - Database operations abstracted for flexibility
4. **Professional Development Workflow** - Git, Azure DevOps, and deployment automation
5. **Production-Ready Service** - Health checks, monitoring, and documentation

### Knowledge Check (5 Multiple Choice Questions):
1. **What is the main advantage of the Repository Pattern?**
   - A) Faster database queries
   - B) Abstracts database operations for easier testing and maintenance
   - C) Reduces memory usage
   - D) Improves API performance

2. **Which deployment method provides automatic CI/CD?**
   - A) Local deployment
   - B) Manual zip upload
   - C) GitHub/Azure DevOps with source control integration
   - D) FTP deployment

3. **Where is the business logic located in this architecture?**
   - A) In the FastAPI endpoints
   - B) In the database repository
   - C) In the service layer (order_service.py)
   - D) In the Pydantic schemas

4. **What file contains the dependency definitions?**
   - A) app.py
   - B) requirements.txt
   - C) setup.py
   - D) Dockerfile

5. **Which deployment method is best for enterprise private repositories?**
   - A) GitHub public repo
   - B) Azure DevOps
   - C) Local zip deployment
   - D) Manual FTP

**Answers: 1-B, 2-C, 3-C, 4-B, 5-B**

### Real-Life Interview Questions:
1. "Compare the three deployment methods you used. When would you choose each one?"
2. "How would you set up CI/CD pipeline for this microservice?"
3. "Explain the folder structure and why you organized the code this way."
4. "How would you handle database migrations in production deployments?"
5. "What monitoring and logging would you add for production readiness?"

---

## Project Structure You Built:

```
order-service/
├── app/
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py      # Database setup and connection
│   │   └── repository.py      # Data access layer
│   ├── models/
│   │   ├── __init__.py
│   │   └── order.py          # SQLAlchemy models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── order.py          # Pydantic schemas
│   └── services/
│       ├── __init__.py
│       ├── eventhub.py       # Event Hub integration
│       └── order_service.py  # Business logic
├── app.py                    # FastAPI application
├── requirements.txt
├── .gitignore
├── README.md
└── orders.db                # SQLite database (created automatically)
```

## Architecture Benefits You Implemented:

✅ **Separation of Concerns** - Each module has a single responsibility  
✅ **Dependency Injection** - Services are injected via FastAPI's dependency system  
✅ **Repository Pattern** - Database operations abstracted in repository layer  
✅ **Service Layer** - Business logic separated from API endpoints  
✅ **Schema Validation** - Pydantic ensures type safety and validation  
✅ **Async Operations** - Non-blocking event publishing and database operations  
✅ **Error Handling** - Proper exception handling at each layer  
✅ **Testability** - Each component can be tested independently  

## Next Session Preview:
**"Tomorrow we'll add Azure Storage Services integration! You'll build:**
- **Queue Storage** for reliable async processing with Python
- **Table Storage** for fast metadata lookups using Azure SDK  
- **File Storage** for handling product images and file uploads
- **Complete storage strategy** that integrates with your Python order events

**You'll also learn how to deploy these storage integrations using your preferred deployment method!"**
