from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging
from datetime import datetime
import threading
import atexit

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Item Management API",
    description="FastAPI application for managing items with persistence",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PERSISTENCE_FILE = "items_backup.json"
lock = threading.Lock()

class Item(BaseModel):
    id: Optional[int] = None
    code: str = Field(..., min_length=1, description="Item code")
    unit: int = Field(..., ge=0, description="Unit quantity")
    age: int = Field(..., ge=0, description="Item age")
    cost: float = Field(..., ge=0, description="Item cost")

    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)
        }

class AddItemRequest(BaseModel):
    id: int = Field(..., description="Item ID")
    code: str = Field(..., min_length=1, description="Item code")
    unit: int = Field(..., ge=0, description="Unit quantity")
    age: int = Field(..., ge=0, description="Item age")
    cost: float = Field(..., ge=0, description="Item cost")

class SortRequest(BaseModel):
    sort_by: Literal["unit", "age", "cost"] = Field(..., description="Field to sort by")

class RemoveRequest(BaseModel):
    id: int = Field(..., description="Item ID to remove")

class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None

in_memory_store: List[Item] = []

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "db-host-001.local"),
            port=os.getenv("DB_PORT", "5678"),
            user=os.getenv("DB_USER", "dbuser"),
            password=os.getenv("DB_PASS", "dbpass"),
            database=os.getenv("DB_NAME", "app001"),
            cursor_factory=RealDictCursor
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")

def test_db_connection():
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")
        return False

def save_to_file():
    try:
        with lock:
            data = {
                "items": [item.dict() for item in in_memory_store],
                "timestamp": datetime.now().isoformat()
            }
            with open(PERSISTENCE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Data saved to {PERSISTENCE_FILE}")
    except Exception as e:
        logger.error(f"Failed to save to file: {e}")

def load_from_file():
    global in_memory_store
    try:
        if os.path.exists(PERSISTENCE_FILE):
            with open(PERSISTENCE_FILE, 'r') as f:
                data = json.load(f)
                in_memory_store = [Item(**item) for item in data.get("items", [])]
                logger.info(f"Loaded {len(in_memory_store)} items from {PERSISTENCE_FILE}")
        else:
            logger.info("No persistence file found, starting with empty store")
    except Exception as e:
        logger.error(f"Failed to load from file: {e}")
        in_memory_store = []

def check_duplicate_in_memory(code: str, unit: int, age: int, cost: float) -> bool:
    for item in in_memory_store:
        if (item.code == code and item.unit == unit and 
            item.age == age and abs(item.cost - cost) < 0.01):
            return True
    return False

def call_stored_procedure(code: str, unit: int, age: int, cost: float) -> tuple:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.callproc("add_call", (code, unit, age, cost))
        result = cur.fetchone()
        conn.commit()
        
        if result:
            return (result['id'], result['status'], result['message'])
        else:
            raise Exception("No result from stored procedure")
            
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Stored procedure error: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Stored procedure error: {str(e)}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

@app.post("/add", response_model=ApiResponse)
async def add_item(request: AddItemRequest):
    try:
        if check_duplicate_in_memory(request.code, request.unit, request.age, request.cost):
            raise HTTPException(
                status_code=400, 
                detail="Duplicate item detected in memory store"
            )
        
        db_available = test_db_connection()
        
        if db_available:
            try:
                row_id, status, message = call_stored_procedure(
                    request.code, request.unit, request.age, request.cost
                )
                
                if status == 0:
                    raise HTTPException(status_code=400, detail=message)
                
                item = Item(
                    id=row_id,
                    code=request.code,
                    unit=request.unit,
                    age=request.age,
                    cost=request.cost
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                item = Item(
                    id=request.id,
                    code=request.code,
                    unit=request.unit,
                    age=request.age,
                    cost=request.cost
                )
                message = "Item added to memory only (database unavailable)"
        else:
            item = Item(
                id=request.id,
                code=request.code,
                unit=request.unit,
                age=request.age,
                cost=request.cost
            )
            message = "Item added to memory only (database unavailable)"
        
        in_memory_store.append(item)
        save_to_file()
        
        return ApiResponse(
            status="success",
            message=message,
            data={"id": item.id, "total_items": len(in_memory_store)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in add_item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/snapshot", response_model=List[Item])
async def get_snapshot(request: SortRequest):
    try:
        if not in_memory_store:
            return []
        
        sorted_items = sorted(
            in_memory_store, 
            key=lambda x: getattr(x, request.sort_by)
        )
        
        logger.info(f"Snapshot retrieved with {len(sorted_items)} items, sorted by {request.sort_by}")
        return sorted_items
        
    except Exception as e:
        logger.error(f"Error in get_snapshot: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve snapshot")

@app.post("/remove", response_model=ApiResponse)
async def remove_item(request: RemoveRequest):
    global in_memory_store
    
    try:
        original_count = len(in_memory_store)
        in_memory_store = [item for item in in_memory_store if item.id != request.id]
        
        if len(in_memory_store) == original_count:
            raise HTTPException(status_code=404, detail="Item not found in memory")
        
        db_available = test_db_connection()
        if db_available:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM items WHERE id = %s", (request.id,))
                rows_affected = cur.rowcount
                conn.commit()
                
                if rows_affected == 0:
                    logger.warning(f"Item {request.id} not found in database")
                    
            except Exception as e:
                logger.error(f"Database removal failed: {e}")
                conn.rollback()
            finally:
                cur.close()
                conn.close()
        
        save_to_file()
        
        return ApiResponse(
            status="success",
            message=f"Item {request.id} removed successfully",
            data={"remaining_items": len(in_memory_store)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in remove_item: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove item")

@app.post("/clear", response_model=ApiResponse)
async def clear_items():
    global in_memory_store
    
    try:
        items_count = len(in_memory_store)
        in_memory_store = []
        
        db_available = test_db_connection()
        if db_available:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("TRUNCATE TABLE items RESTART IDENTITY")
                conn.commit()
                logger.info("Database cleared successfully")
            except Exception as e:
                logger.error(f"Database clear failed: {e}")
                conn.rollback()
            finally:
                cur.close()
                conn.close()
        
        save_to_file()
        
        return ApiResponse(
            status="success",
            message=f"All items cleared successfully ({items_count} items removed)",
            data={"items_cleared": items_count}
        )
        
    except Exception as e:
        logger.error(f"Error in clear_items: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear items")

@app.get("/health")
async def health_check():
    db_status = "connected" if test_db_connection() else "disconnected"
    return {
        "status": "healthy",
        "database": db_status,
        "items_in_memory": len(in_memory_store),
        "timestamp": datetime.now().isoformat()
    }

@app.on_event("startup")
async def startup_event():
    logger.info("Starting FastAPI application...")
    load_from_file()
    logger.info(f"Application started with {len(in_memory_store)} items in memory")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    save_to_file()
    logger.info("Application shutdown complete")

atexit.register(save_to_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)