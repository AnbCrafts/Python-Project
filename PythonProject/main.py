import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

# Load environment variables
load_dotenv()

# --- DATABASE SETUP ---
db_client = None
db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Equivalent to mongoose.connect()
    global db_client, db
    mongo_uri = os.getenv("MONGODB_URI")
    db_client = AsyncIOMotorClient(mongo_uri)
    db = db_client.exposcan  # Name of your database
    yield
    # Equivalent to mongoose.disconnect()
    db_client.close()

app = FastAPI(lifespan=lifespan)

# --- PYDANTIC SCHEMAS (Validation) ---
class LeadSource(str, Enum):
    trade_show = "trade show"
    website = "website"
    referral = "referral"

class LeadCreate(BaseModel):
    company_name: str = Field(..., min_length=1, description="Company name is required")
    contact_person: str = Field(..., min_length=1, description="Contact person is required")
    email: EmailStr = Field(..., description="Must be a valid email address")
    source: LeadSource

# --- API ENDPOINTS ---
@app.post("/leads", status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate, 
    request: Request, 
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    """
    Creates a new lead. Requires an Idempotency-Key header to prevent duplicate creations.
    """
    # 1. Check for Idempotency Key in the database
    existing_request = await db.idempotency_keys.find_one({"_id": idempotency_key})
    
    if existing_request:
        # If the key exists, fetch the original lead it created
        original_lead = await db.leads.find_one({"_id": existing_request["lead_id"]})
        
        if original_lead:
            # Convert MongoDB ObjectId to string for JSON serialization
            original_lead["_id"] = str(original_lead["_id"])
            
            # Return 200 OK (instead of 201) to indicate it was already processed
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Lead already created with this Idempotency-Key.",
                    "data": original_lead
                }
            )

    # 2. Prepare the new lead document
    # Convert Pydantic model to a standard dictionary
    new_lead = payload.model_dump()
    
    # Strictly set the created_at timestamp on the server in UTC
    new_lead["created_at"] = datetime.now(timezone.utc)

    # 3. Insert the new lead into the database
    try:
        lead_result = await db.leads.insert_one(new_lead)
        lead_id = lead_result.inserted_id
        
        # 4. Save the Idempotency Key so it cannot be used again
        await db.idempotency_keys.insert_one({
            "_id": idempotency_key,
            "lead_id": lead_id,
            "created_at": datetime.now(timezone.utc)
        })

        # Convert IDs and dates for the final JSON response
        new_lead["_id"] = str(lead_id)
        new_lead["created_at"] = new_lead["created_at"].isoformat()

        return {"message": "Lead successfully created.", "id": str(lead_id)}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Database transaction failed.")