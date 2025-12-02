import json
import itertools
from sage.all import *

q = 251
n = 16
k = 2
P = PolynomialRing(GF(q), 'x')
x = P.gen()
R = P.quotient_ring(x**n + 1)
X = R.gen()

keys = json.load(open("./task/keys.json"))
A = matrix(R, k, k, keys["A"])
t = vector(R, k, keys["t"])
u_list = [vector(R, k, u) for u in keys["u"]]
v_list = [R(v) for v in keys["v"]]

def round_q(m):
	return [0 if abs(coeff) < q/4 else 1 for coeff in vector(m).lift_centered()]

def gen_poly(weight=2):
	for i, j in itertools.combinations(range(n), weight):
		for b1, b2 in itertools.product([-1, 1], repeat=2):
			poly = [0] * n
			poly[i] = b1
			poly[j] = b2
			yield poly

def check_error(e):
	for poly in e:
		if not all(coeff in [-1, 0, 1] for coeff in vector(poly).lift_centered()):
			return False
	return True

def bf(u, v):
	for r in itertools.product(gen_poly(), repeat=k):
		r = vector(R, k, r)
		e = u - A.transpose() * r
		if check_error(e):
			m = round_q(v - t*r)
			return int(Integer(m[::-1], 2)).to_bytes(n//8).decode()

flag = ""

for u, v in zip(u_list, v_list):
	flag += "".join(bf(u,v))

print(flag)