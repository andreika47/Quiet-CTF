from sage.all import *
import hashlib
 
R = LaurentPolynomialRing(QQ, 't')
t = R.gen()
 
def sweep(ap):
    l = len(ap)
    current_row = [0] * l
    mat = []
    for pair in ap:
        c1, c2 = sorted(pair)
        diff = pair[1] - pair[0]
        s = (diff > 0) - (diff < 0)
        for c in range(c1, c2):
            current_row[c] += s
        mat.append(list(current_row))
    return mat
 
def calculate(point):
    x, o = point
    n = len(x)
    data = sweep(list(zip(x, o)))
    mat = matrix(R, [[t**(-v) for v in row] for row in data])
    F = R.fraction_field()
    return R(F(mat.det()) * F(1-t)**(1-n))
 
def normalize(calc):
    poly = R(calc)
    min_exp = min(poly.exponents())
    poly *= t**(-min_exp)
    if poly.constant_coefficient() < 0:
        poly = -poly
    return poly
 
# Открыте ключи и шифртекст
alice_pub = ([8,15,7,26,1,4,2,12,9,18,23,25,24,14,13,16,0,3,11,10,5,20,6,21,19,17,22],
             [5,2,23,3,25,9,26,8,24,7,14,18,12,4,20,21,6,1,19,22,10,0,16,17,15,11,13])
bob_pub = ([26,9,21,4,28,8,20,7,27,1,13,25,22,17,6,15,24,3,12,29,11,16,10,0,18,2,14,5,19,23],
           [5,18,28,27,25,19,23,13,21,24,16,15,8,29,14,11,26,22,9,7,10,3,2,6,0,12,17,20,1,4])
public_info = ([11,0,2,4,8,3,1,10,7,6,9,5],[1,9,8,10,11,7,4,6,5,3,2,0])
ct = "288cdf5ecf3eb860e2cb6790bff63baceaebb6ed511cd94dd0753bac59962ef0cd171231dc406ac3cdc2ff299d78390ff3"
 
# Вычисляем инварианты
pub_inv   = normalize(calculate(public_info))
alice_inv = normalize(calculate(alice_pub))
bob_inv   = normalize(calculate(bob_pub))
 
F = R.fraction_field()
shared_inv = normalize(R(F(alice_inv) * F(bob_inv) / F(pub_inv)))
 
# Вычисляем хэш
import sympy
st = sympy.Symbol('t', real=True, positive=True)
sympy_poly = sum(int(c) * st**int(e) for e, c in shared_inv.dict().items())
sympy_norm = sympy.expand(sympy_poly)
if sympy_norm.coeff(st, 0) < 0:
    sympy_norm *= -1
 
shared = hashlib.sha256(str(sympy_norm).encode()).hexdigest()
key = bytes.fromhex(shared)
while len(key) < len(ct)//2:
    key += hashlib.sha256(key).digest()
print(bytes(a^b for a, b in zip(bytes.fromhex(ct), key)))