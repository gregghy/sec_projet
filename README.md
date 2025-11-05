

## Technologies Used

### **Frontend**
- **React** 
- **Tailwind CSS** 

### **Backend**
- **Python 3 + FastAPI** 
- **JSON file storage (`data.json`)** 

### **Encryption**
- **Python Scripts**


## 3. System Architecture

```
Browser (React)  ⇄  FastAPI Python Server  ⇄  data.json
   ↑                    ↑
   │                    │
   └── REST / WebSocket ┘
```

- **The Client** communicates with the **Server** through HTTPS and WebSocket. The WebPage is shared with HTTPS while real time auction information are delivered through WebSocket.  
- **Backend** reads/writes auction data and user data from/to a local JSON file.  

---

## 4. Data Storage Format

All persistent information is stored in JSON files.

```json
{
  "users": [
    {
      "username": "alice",
      "password_hash": "sha256_hash_here",
      "selling": "auction_id"
    }
  ],
  "auctions": [
    {
      "id": "auction_id",
      "item": "auction_title",
      "seller": "username_hash",
      "highest_bid": 150,
      "highest_bidder": "username_hash",
      "status": "open",
      "time_remaining": 120
    }
  ]
}
```


## 5. Communication Protocol

All messages between client and server travel through:
- **REST API** (HTTP)
- **WebSocket** (`ws://` or `wss://` for real-time events)

---

### 5.1 User Operations

### **Register**

**Request**
```
POST /register
Content-Type: application/json
```

```json
{
  "username": "username",
  "password": "password_hash"
}
```

**Response**
```json
{
  "status": "registered"
}
```

---

### **Login**

**Request**
```
POST /login
```

```json
{
  "username": "username",
  "password": "password_hash"
}
```

**Response**
```json
{
  "status": "ok"
}
```

---

### 5.2 Auction Operations

### **List Active Auctions**

**Request**
```
GET /auctions
```

**Response**
```json
[
  {
    "id": "auction_id",
    "item": "auction_title",
    "seller": "username_hash",
    "highest_bid": 150,
    "highest_bidder": "username_hash",
    "status": "open",
    "time_remaining": 120
  },
  {
    "id": "auction_id",
    "item": "auction_title",
    "seller": "username_hash",
    "highest_bid": 80,
    "highest_bidder": "username_hash",
    "status": "open",
    "time_remaining": 49
  }
]
```
---
### **Get Auction Status**

**Request**
```
GET /auction_id
```

**Response**
```json
 {
   "id": "auction_id",
   "item": "auction_title",
   "seller": "username_hash",
   "highest_bid": 150,
   "highest_bidder": "username_hash",
   "status": "open",
   "time_remaining": 120
 }
```
---

### **Place a Bid**

**Request**
```
POST /bid
Content-Type: application/json
```

```json
{
  "id": "auction_id",
  "bidder": "username_hash",
  "amount": 200
}
```

**Response**
```json
{
  "status": "accepted",
  "new_highest": 200
}
```

If bid is too low :
```json
{
	"status": "refused",
  "detail": "Bid too low"
}
```

---

### **Create Auction**

**Request**
```
POST /auction
Content-Type: application/json
```

```json
{
  "id": "auction_id",
  "item": "auction_title",
  "seller": "username_hash",
  "highest_bid": MIN_OFFER,
  "highest_bidder": void,
  "time_remaining": MAX_TIME,
}
```

**Response**
```json
{
  "status": "accepted",
  "new_highest": MIN_OFFER
}
```

---

### 5.3 Real-Time Updates (WebSocket)

Clients connect to:
```
ws://<server_address>:8000/ws
```

When a bid is placed, the server broadcasts a message to all connected clients.

**Broadcast Message Example**
```json
{
  "event": "NEW_BID",
  "id": "auction_id",
  "bidder": "username_hash",
  "amount": 200,
  "timestamp": "2025-11-03 12:30:00"
}
```


## 6. Security and Trust

| Concept | Description |
|----------|--------------|
| **Encryption** | Use symmetric encryption to have fast and secure communication between client-server (AES-128). |
| **Key-Exchange** | Asymmetric key is used to securely exchange the symmetric one |
| **Passwords** | Passwords are stored as SHA-256 hashes. |
| **Fairness** | All bids are timestamped and broadcast to all participants. |

---

## 7. Protocol Requests

1. User registers → `POST /register`  
2. User logs in → `POST /login`  
3. Frontend fetches active auctions → `GET /auctions`  
4. Fetch auction info → `GET /auction_id`
5. User places a bid → `POST /bid`  
6. User places an auction → `POST /auction`
7. Server updates `data.json` and broadcasts event → WebSocket message sent to all clients  



