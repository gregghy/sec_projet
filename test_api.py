import requests
import json
import base64
import time
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://localhost:8000"

# --- Security Helpers ---

def encrypt_data(data, aes_key):
    json_str = json.dumps(data)
    iv = get_random_bytes(16)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(json_str.encode('utf-8'), AES.block_size))
    return base64.b64encode(iv + ct).decode('utf-8')

def decrypt_data(encrypted_b64, aes_key):
    encrypted_data = base64.b64decode(encrypted_b64)
    iv = encrypted_data[:16]
    ct = encrypted_data[16:]
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return json.loads(pt.decode('utf-8'))

def test_api():
    print("Testing API with Security...")
    
    # 1. Get Public Key
    print("1. Fetching Public Key...")
    try:
        resp = requests.get(f"{BASE_URL}/public-key", verify=False)
    except requests.exceptions.ConnectionError:
        print("Failed to connect to server.")
        return

    if resp.status_code != 200:
        print("Failed to get public key")
        return
    public_key_pem = resp.json()["key"]
    public_key = RSA.import_key(public_key_pem)
    print("   Public Key received.")

    # 2. Handshake
    print("2. Performing Handshake...")
    aes_key = get_random_bytes(32) # 256-bit key
    
    cipher_rsa = PKCS1_v1_5.new(public_key)
    enc_key = cipher_rsa.encrypt(aes_key)
    enc_key_b64 = base64.b64encode(enc_key).decode('utf-8')
    
    resp = requests.post(f"{BASE_URL}/handshake", json={"encrypted_key": enc_key_b64}, verify=False)
    if resp.status_code != 200:
        print(f"Handshake failed: {resp.text}")
        return
    session_id = resp.json()["session_id"]
    print(f"   Handshake successful. Session ID: {session_id}")
    
    headers = {"X-Session-ID": session_id}

    # 3. Register
    print("3. Registering User...")
    payload = {"username": "testuser_sec", "password": "password123"}
    encrypted_payload = encrypt_data(payload, aes_key)
    
    resp = requests.post(f"{BASE_URL}/register", json={"data": encrypted_payload}, headers=headers, verify=False)
    if resp.status_code == 200:
        data = decrypt_data(resp.json()["data"], aes_key)
        print(f"   Register success: {data}")
    elif resp.status_code == 400: # Already exists
        print("   User already exists (expected if re-running)")
    else:
        print(f"   Register failed: {resp.text}")

    # 4. Login
    print("4. Logging in...")
    payload = {"username": "testuser_sec", "password": "password123"}
    encrypted_payload = encrypt_data(payload, aes_key)
    
    resp = requests.post(f"{BASE_URL}/login", json={"data": encrypted_payload}, headers=headers, verify=False)
    if resp.status_code == 200:
        data = decrypt_data(resp.json()["data"], aes_key)
        print(f"   Login success: {data}")
    else:
        print(f"   Login failed: {resp.text}")

    # 5. Create Auction
    print("5. Creating Auction...")
    auction_id = f"auc_sec_{int(time.time())}"
    payload = {
        "id": auction_id,
        "item": "Secure Item",
        "description": "Encrypted auction",
        "seller": "testuser_sec",
        "min_price": 100,
        "time_remaining": 60
    }
    encrypted_payload = encrypt_data(payload, aes_key)
    
    resp = requests.post(f"{BASE_URL}/auction", json={"data": encrypted_payload}, headers=headers, verify=False)
    if resp.status_code == 200:
        data = decrypt_data(resp.json()["data"], aes_key)
        print(f"   Create Auction success: {data}")
    else:
        print(f"   Create Auction failed: {resp.text}")

    # 6. List Auctions
    print("6. Listing Auctions...")
    resp = requests.get(f"{BASE_URL}/auctions", headers=headers, verify=False)
    if resp.status_code == 200:
        data = decrypt_data(resp.json()["data"], aes_key)
        print(f"   Auctions found: {len(data)}")
    else:
        print(f"   List Auctions failed: {resp.text}")

if __name__ == "__main__":
    test_api()
