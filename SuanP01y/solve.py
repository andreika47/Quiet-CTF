from sage.all import *
from Crypto.Cipher import AES
from hashlib import md5
from itertools import combinations
from collections import defaultdict
import os
import sys
sys.setrecursionlimit(20000)

r, d = 16381, 41
R = PolynomialRing(GF(2), 'x')
x = R.gen()
S = R.quotient(x**r - 1, 'X')
X = S.gen()
m = x**r - 1

def hwt(p): 
	return len(p.exponents())

def min_arc_len(exps, n=r):
	"""Минимальная длина циклического интервала, покрывающего все экспоненты"""
	if not exps: return 0
	exps = sorted(e % n for e in exps)
	gaps = [ (exps[(i+1)%len(exps)] - exps[i]) % n for i in range(len(exps)) ]
	return n - max(gaps)

def in_window(p, lim=r//3):
	return min_arc_len(p.exponents(), r) <= lim

def rotate_R(p, s):

	s %= r
	return R((S(p) * (X**s)).lift())

def try_reconstruct_once(qR):
	l0, l1 = m, qR
	j0, j1 = R(1), R(0)
	k0, k1 = R(0), R(1)
	while l1 != 0:
		qout, rem = l0.quo_rem(l1)
		l0, l1 = l1, rem
		j0, j1 = j1, j0 - qout*j1
		k0, k1 = k1, k0 - qout*k1
		A, B = l0, k0
		# Проверяем условия на вес и окно
		if hwt(A) == d and hwt(B) == d and in_window(A) and in_window(B):
			# Проверяем два возможных соотношения: q * B
			U = R((S(qR) * S(B)).lift())	   
			if hwt(U) == d and A != 0 and U != 0:
				Delta = (U.exponents()[0] - A.exponents()[0]) % r
				if rotate_R(A, Delta) == U:	# проверяем соотношение со сдвигом
					return A, B, Delta
			# или q * A
			U2 = R((S(qR) * S(A)).lift())
			if hwt(U2) == d and B != 0 and U2 != 0:
				Delta = (U2.exponents()[0] - B.exponents()[0]) % r
				if rotate_R(B, Delta) == U2:
					return B, A, Delta
	return None

def rational_reconstruct(qR):
	res = try_reconstruct_once(qR)
	if res is not None:
		return res

	# если ничего не нашли, то пробуем со сдвигом
	shift = r//3 + 1
	qR_shift = rotate_R(qR, shift)
	res = try_reconstruct_once(qR_shift)
	if res:
		A, B, Delta = res

		A = rotate_R(A, r - shift)
		return A, B, Delta

	return None, None, None

print("START")

with open("./task/output.txt", "r") as f:
	data = f.read().splitlines()
	hint_str = data[0].split(" = ")[1]
	ciphertext_hex = data[1]

# print(hint_str)
# print(ciphertext_hex)

hintS = S(hint_str)	# получаем полином над S
hintR = R(hintS.lift())	 # получаем каноническое представление полинома над R
ciphertext = bytes.fromhex(ciphertext_hex)

print("ATTACK")

A, B, Delta = rational_reconstruct(hintR)

if B:
	assert gcd(B, m) == 1

	for k0 in range(r):
		h0 = S(B) * (X**k0)
		key = md5(str(h0).encode()).digest()
		pt = AES.new(key=key, mode=AES.MODE_CTR, nonce=b"suanp01y").decrypt(ciphertext)
		if pt.startswith(b"RCTF{") and pt.endswith(b"}"):
			print("flag =", pt.decode())
			print("k0  =", k0)
			break
else:
	print("FAILED")