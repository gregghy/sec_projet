
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
from RSA import RSA as CustomRSA
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

# Custom RSA Key Generation
custom_rsa = CustomRSA(1024)
(e, n) = custom_rsa.public

#DER Encoder for RSA Public Key
def encode_length(length):
    if length < 128:
        return bytes([length])
    else:
        length_bytes = length.to_bytes((length.bit_length() + 7) // 8, 'big')
        return bytes([0x80 | len(length_bytes)]) + length_bytes

def encode_integer(int_val):
    val_bytes = int_val.to_bytes((int_val.bit_length() + 7) // 8, 'big')
    if val_bytes[0] & 0x80:
        val_bytes = b'\x00' + val_bytes
    return b'\x02' + encode_length(len(val_bytes)) + val_bytes

def encode_sequence(content):
    return b'\x30' + encode_length(len(content)) + content

def encode_bitstring(content):
    return b'\x03' + encode_length(len(content) + 1) + b'\x00' + content

def export_public_key_pem(n, e):
    rsa_public_key = encode_sequence(encode_integer(n) + encode_integer(e))
    
    alg_id = b'\x30\x0d\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01\x05\x00'
    
    spki = encode_sequence(alg_id + encode_bitstring(rsa_public_key))
    
    b64_spki = base64.b64encode(spki).decode('utf-8')
    
    pem_lines = ["-----BEGIN PUBLIC KEY-----"]
    for i in range(0, len(b64_spki), 64):
        pem_lines.append(b64_spki[i:i+64])
    pem_lines.append("-----END PUBLIC KEY-----")
    return "\n".join(pem_lines)

public_key_pem = export_public_key_pem(n, e)

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
    return {"key": public_key_pem}

class HandshakeRequest(BaseModel):
    encrypted_key: str

@app.post("/handshake")
def handshake(req: HandshakeRequest):
    try:
        enc_key = base64.b64decode(req.encrypted_key)
        
        #RSA Raw Decryption
        c_int = int.from_bytes(enc_key, 'big')
        (d, n) = custom_rsa.private
        m_int = pow(c_int, d, n)
        
        key_length_bytes = (n.bit_length() + 7) // 8
        decrypted_block = m_int.to_bytes(key_length_bytes, 'big')
        
        #PKCS#1 v1.5 Unpadding
        #00 02 [padding] 00 [aes_key]
        try:
            sep_index = decrypted_block.find(b'\x00', 2)
            if sep_index == -1:
                raise Exception("Padding error: separator not found")
            
            aes_key_bytes = decrypted_block[sep_index+1:]
            aes_key = base64.b64decode(aes_key_bytes)
            
        except Exception as e:
            print(f"Unpadding/Decoding error: {e}")
            raise HTTPException(status_code=400, detail="Handshake failed")

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

