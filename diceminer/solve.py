import requests
import sys
import random
import string
import hashlib

MAX_INT = 9007199254740991
FLAG_COST = 1000000
WORLD_SEED = 42
PICKAXES = [
    {"name": "Wooden Pickaxe", "range": 5, "cost": 0, "tier": 0},
    {"name": "Stone Pickaxe", "range": 15, "cost": 100, "tier": 1},
    {"name": "Iron Pickaxe", "range": 40, "cost": 500, "tier": 2},
    {"name": "Gold Pickaxe", "range": 100, "cost": 5000, "tier": 3},
]
BASE_URL = "http://0.0.0.0:8080"

def is_diamond(x, y):
    s = f"{WORLD_SEED}:{x}:{y}"
    h = hashlib.md5(s.encode()).digest()
    r = int.from_bytes(h[:4], 'big') / 0xFFFFFFFF
    return y <= -50 and r < 0.04

def get_state(s):
    r = s.get(f"{BASE_URL}/api/state")
    assert r.ok, f"Get state failed: {r.text}"
    return r.json()

def dig(s, direction):
    r = s.post(f"{BASE_URL}/api/dig", json={"direction": direction})
    assert r.ok, f"Dig failed: {r.text}"

def move_deeper(s, x, y):
    r = s.post(f"{BASE_URL}/api/move", json={"x": x, "y": y})
    return r.ok

def buy(s, item):
    r = s.post(f"{BASE_URL}/api/buy", json={"item": item})
    assert r.ok, f"Buying failed: {r.text}"
    r = r.json()
    if 'flag' in r:
        return r['flag']
    return None

def solve():
    s = requests.Session()

    username = "".join(random.choices(string.ascii_lowercase, k=8))
    password = "".join(random.choices(string.ascii_lowercase, k=8))

    r = s.post(f"{BASE_URL}/api/register", json={"username": username, "password": password})
    assert r.ok, f"Registration failed: {r.text}"
    print(f"{username}:{password}")

    r = s.post(f"{BASE_URL}/api/start", json={"x": MAX_INT})
    assert r.ok, f"Start failed: {r.text}"

    mined = 0
    state = get_state(s)
    print(f"{state['x']} {state['y']}\n{state['pickaxe']}\n{state['balance']}\n{state['energy']}")

    while state['pickaxe'] < len(PICKAXES) - 1:
        if state['y'] - 1 <= mined:
            dig(s, 'down')
            mined = state['y'] - PICKAXES[state['pickaxe']]['range']
            print(f"{mined = }")
        else:
            if move_deeper(s, state['x'], state['y'] - 1):
                dig(s, 'right')
            else:
                dig(s, 'down')
                mined = state['y'] - PICKAXES[state['pickaxe']]['range']
                move_deeper(s, state['x'], state['y'] - 1)
                dig(s, 'right')

        state = get_state(s)
        if state['balance'] >= FLAG_COST:
            flag = buy(s, "flag")
            print(flag)
            break
        if state['pickaxe'] < len(PICKAXES) - 1 and state['balance'] >= PICKAXES[state['pickaxe'] + 1]['cost']:
            buy(s, str(state['pickaxe'] + 1))

    state = get_state(s)
    print(f"{state['x']} {state['y']}\n{state['pickaxe']}\n{state['balance']}\n{state['energy']}")

    best_way = []
    DOWN_DIGS = 0
    cur_y = state['y']
    while len(best_way) + DOWN_DIGS < state['energy']:
        if cur_y - 1 <= mined - PICKAXES[state['pickaxe']]['range'] * DOWN_DIGS:
            DOWN_DIGS += 1
        else:
            cur_y -= 1
            if is_diamond(state['x'] + 1, cur_y):
                best_way.append(cur_y)

    print(best_way)
    for p in best_way:
        while state['y'] > p:
            if not move_deeper(s, state['x'], state['y'] - 1):
                dig(s, 'down')
            state = get_state(s)

        dig(s, 'right')
        state = get_state(s)
        if state['balance'] >= FLAG_COST:
            break

    state = get_state(s)
    print(f"{state['x']} {state['y']}\n{state['pickaxe']}\n{state['balance']}\n{state['energy']}")
    flag = buy(s, 'flag')
    print(flag)

if __name__ == "__main__":
    solve()