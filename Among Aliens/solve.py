from sage.all import *
import requests
import base64
import json
import random

base_url = "http://cyberctf.tech:11000/"

try:
	session = requests.Session()
	resp = session.get(f"{base_url}/api/game/start")
	session_id = resp.headers['Set-Cookie']
	session_id = session_id.split('alien_game_session=')[1]
	session_id = session_id.split('.')[0]

	try:
		session_id = base64.b64decode(session_id)
	except:
		try:
			session_id = base64.b64decode(session_id + '=')
		except:
			try:
				session_id = base64.b64decode(session_id + '==')
			except Exception as be:
				print(f"[BASE64 ERROR]: {be}")
	session_id = json.loads(session_id)
	session_id = session_id["session_id"]
	print(session_id)

	resp = session.get(f"{base_url}/api/images/..%2fmatrix-data/{session_id}.json")
	matrix_str = resp.json()['matrix']
except Exception as e:
	print(f"[ERROR]: {e}")

k = 32
C = []
matrix_str = matrix_str.split('\n')

for l in matrix_str:
	l = l.replace('    ', ' ')
	l = l.replace('   ', ' ')
	l = l.replace('  ', ' ')
	l = l.replace('  ', ' ')
	l = l.replace('   ', ' ')
	l = l.replace('[ ', '[')
	l = l[1 : -1]
	C += [i for i in l.split(' ')]

C = matrix(QQ, k, k, C)
evs = C.eigenvalues()
seed = 1

for ev in evs:
	seed *= int(ev)

random.seed(seed)
K = [random.randint(0, 255) for _ in range(k * k)]
K = matrix(QQ, k, k, K)
M = K.inverse() * C * K

flag_text = ""

for i in range(k):
	flag_text += chr(M[i][i])

print("flag{" + flag_text + "}")
