import json
import numpy as np

q = 3329
n = 512
k = 4
F = GF(q)
P = F[]
x = P.gen()
R = P.quotient_ring(x**n + 1)
X = R.gen()

keys = json.load(open("./task/keys.json"))
A1 = matrix(R, k, k, np.array(keys["A_1"]).T[:k].tolist())
t1 = vector(R, k, keys["t_1"])
A2 = matrix(R, k, k, np.array(keys["A_2"]).T[:k].tolist())
t2 = vector(R, k, keys["t_2"])
u1 = vector(R, k, keys["u_1"])
u2 = vector(R, k, keys["u_2"])
v1 = R(keys["v_1"])
v2 = R(keys["v_2"])

def round_q(m):
    return [0 if abs(coeff) < q/4 else 1 for coeff in vector(m).lift_centered()]

r = (A1 - A2)**(-1) * (u1 - u2)
m = round_q(v1 - t1*r)
flag = Integer(m[::-1], 2).to_bytes(n//8).decode()
print(flag)
