
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import time
import asyncio
import hashlib
import os
import uuid
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "data.json"

#Sec

key = RSA.generate(2048)
private_key = key
public_key = key.publickey()

SESSIONS: Dict[str, bytes] = {}

#Data classes

class User(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Auction(BaseModel):
    id: str
    item: str
    description: Optional[str] = ""
    seller: str
    highest_bid: int
    highest_bidder: Optional[str] = None
    status: str
    time_remaining: int
    start_time: Optional[float] = None

class Bid(BaseModel):
    id: str
    bidder: str
    amount: int

class CreateAuction(BaseModel):
    id: str
    item: str
    description: Optional[str] = ""
    seller: str
    min_price: int
    time_remaining: int

class EncryptedRequest(BaseModel):
    data: str

#Save data

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": [], "auctions": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

#WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

#Timer

async def auction_timer_loop():
    while True:
        data = load_data()
        changed = False
        
        for auction in data["auctions"]:
            if auction["status"] == "open":
                if auction["time_remaining"] > 0:
                    auction["time_remaining"] -= 1
                    changed = True
                else:
                    auction["status"] = "closed"
                    changed = True
                    # Broadcast END event
                    await manager.broadcast({
                        "event": "END",
                        "id": auction["id"],
                        "highest_bid": auction["highest_bid"],
                        "highest_bidder": auction["highest_bidder"]
                    })
        
        if changed:
            save_data(data)
            
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(auction_timer_loop())

#Sec help functions

def decrypt_data(encrypted_b64: str, aes_key: bytes) -> dict:
    try:
        encrypted_data = base64.b64decode(encrypted_b64)
        iv = encrypted_data[:16]
        ct = encrypted_data[16:]
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return json.loads(pt.decode('utf-8'))
    except Exception as e:
        print(f"Decryption error: {e}")
        raise HTTPException(status_code=400, detail="Decryption failed")

def encrypt_data(data: Any, aes_key: bytes) -> str:
    json_str = json.dumps(data)
    iv = get_random_bytes(16)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(json_str.encode('utf-8'), AES.block_size))
    return base64.b64encode(iv + ct).decode('utf-8')

#Endpoints

@app.get("/public-key")
def get_public_key():
    return {"key": public_key.export_key().decode('utf-8')}

class HandshakeRequest(BaseModel):
    encrypted_key: str

@app.post("/handshake")
def handshake(req: HandshakeRequest):
    try:
        enc_key = base64.b64decode(req.encrypted_key)
        cipher_rsa = PKCS1_v1_5.new(private_key)
        sentinel = get_random_bytes(16)
        decrypted_blob = cipher_rsa.decrypt(enc_key, sentinel)
        
        try:
            aes_key = base64.b64decode(decrypted_blob)
        except:
            aes_key = decrypted_blob

        if len(aes_key) not in [16, 24, 32]:
             pass

        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = aes_key
        return {"session_id": session_id}
    except Exception as e:
        print(f"Handshake error: {e}")
        raise HTTPException(status_code=400, detail="Handshake failed")

def get_decrypted_body(req: EncryptedRequest, x_session_id: str):
    if x_session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Invalid Session")
    return decrypt_data(req.data, SESSIONS[x_session_id])

@app.post("/register")
def register(req: EncryptedRequest, x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    if not x_session_id or x_session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Session required")
    
    body = decrypt_data(req.data, SESSIONS[x_session_id])
    user = User(**body)
    
    data = load_data()
    for u in data["users"]:
        if u["username"] == user.username:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    data["users"].append(user.dict())
    save_data(data)
    
    resp = {"status": "registered"}
    return {"data": encrypt_data(resp, SESSIONS[x_session_id])}

@app.post("/login")
def login(req: EncryptedRequest, x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    if not x_session_id or x_session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Session required")

    body = decrypt_data(req.data, SESSIONS[x_session_id])
    user = UserLogin(**body)

    data = load_data()
    for u in data["users"]:
        if u["username"] == user.username and u["password"] == user.password:
             resp = {"status": "ok"}
             return {"data": encrypt_data(resp, SESSIONS[x_session_id])}
             
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/auctions")
def get_auctions(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    if not x_session_id or x_session_id not in SESSIONS:
         raise HTTPException(status_code=401, detail="Session required")
         
    data = load_data()
    resp = data["auctions"]
    return {"data": encrypt_data(resp, SESSIONS[x_session_id])}

@app.get("/auction/{auction_id}")
def get_auction(auction_id: str, x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    if not x_session_id or x_session_id not in SESSIONS:
         raise HTTPException(status_code=401, detail="Session required")

    data = load_data()
    for auction in data["auctions"]:
        if auction["id"] == auction_id:
            return {"data": encrypt_data(auction, SESSIONS[x_session_id])}
    raise HTTPException(status_code=404, detail="Auction not found")

@app.post("/bid")
async def place_bid(req: EncryptedRequest, x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    if not x_session_id or x_session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Session required")
        
    body = decrypt_data(req.data, SESSIONS[x_session_id])
    bid = Bid(**body)
    
    data = load_data()
    found = False
    for auction in data["auctions"]:
        if auction["id"] == bid.id:
            found = True
            if auction["status"] != "open":
                raise HTTPException(status_code=400, detail="Auction is closed")
            if auction["time_remaining"] <= 0:
                raise HTTPException(status_code=400, detail="Auction time expired")
            
            if bid.amount <= auction["highest_bid"]:
                raise HTTPException(status_code=400, detail="Bid too low")
            
            auction["highest_bid"] = bid.amount
            auction["highest_bidder"] = bid.bidder
            
            save_data(data)
            
            await manager.broadcast({
                "event": "NEW_BID",
                "id": auction["id"],
                "bidder": auction["highest_bidder"],
                "amount": auction["highest_bid"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            resp = {"status": "accepted", "new_highest": bid.amount}
            return {"data": encrypt_data(resp, SESSIONS[x_session_id])}
            
    if not found:
        raise HTTPException(status_code=404, detail="Auction not found")

@app.post("/auction")
async def create_auction(req: EncryptedRequest, x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    if not x_session_id or x_session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Session required")

    body = decrypt_data(req.data, SESSIONS[x_session_id])
    auction = CreateAuction(**body)

    data = load_data()
    for a in data["auctions"]:
        if a["id"] == auction.id:
            raise HTTPException(status_code=400, detail="Auction ID already exists")
            
    new_auction = {
        "id": auction.id,
        "item": auction.item,
        "description": auction.description,
        "seller": auction.seller,
        "highest_bid": auction.min_price,
        "highest_bidder": None,
        "status": "open",
        "time_remaining": auction.time_remaining
    }
    
    data["auctions"].append(new_auction)
    save_data(data)
    
    #Broadcast creation
    await manager.broadcast({
        "event": "CREAT",
        "id": new_auction["id"]
    })
    
    resp = {"status": "accepted", "new_highest": auction.min_price}
    return {"data": encrypt_data(resp, SESSIONS[x_session_id])}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

