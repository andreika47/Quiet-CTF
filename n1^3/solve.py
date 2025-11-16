from sage.all import *
import itertools
from collections import Counter
import sys
sys.setrecursionlimit(20000)

Q = 257
F = GF(Q)

def poly_to_tensor(polys, n):
	S = [dict() for _ in range(n)]

	for i, poly in enumerate(polys):
		for coeff, monom in zip(poly.coefficients(), poly.monomials()):
			if monom.degree() == 3:  # рассматриваем мономы степени 3
				idxs = []
				for j, exp in enumerate(monom.exponents()[0]):
					idxs.extend([j] * exp)

				if len(idxs) == 3:
					sorted_idxs = tuple(sorted(idxs))
					cnt = Counter(sorted_idxs)
					mult = 6
					for v in cnt.values():
						mult //= factorial(v)
					
					inv_mult = pow(mult, -1, Q)
					perms = set(itertools.permutations(sorted_idxs))
					for p in perms:
						S[i][p] = (S[i].get(p,0) + coeff * inv_mult) % Q

	return S

def Jennrich_algorithm(S, n, max_atts=50):
	for _ in range(max_atts):
		a = [F.random_element() for _ in range(n)]
		b = [F.random_element() for _ in range(n)]
		c = [F.random_element() for _ in range(n)]
		Sc = {}
		A = matrix(F, n, n)
		B = matrix(F, n, n)

		for i, Sm in enumerate(S):
			if c[i] != 0:
				for idx, val in Sm.items():
					Sc[idx] = (Sc.get(idx,0) + c[i] * val) % Q

		for (p,q,r), val in Sc.items():
			A[p,q] = (A[p,q] + val * a[r]) % Q
			B[p,q] = (B[p,q] + val * b[r]) % Q

		if B.is_invertible():
			X = A * B.inverse()

			try:
				eig_data = X.eigenvectors_right()
				
				if len(eig_data) == n:
					V = matrix(F, n, n)
					for i, (eigenval, eigenvectors, mult) in enumerate(eig_data):
						vec = vector(F, eigenvectors[0])
						V.set_column(i, vec)
				
					return V
					
			except Exception as e:
				print(f"  Error in eigenvalue computation: {e}")
				continue

	return None

if __name__ == "__main__":
	with open('./task/output.txt', 'r') as f:
		lines = f.readlines()

	# Парсинг полиномов и чисел
	poly_str = lines[0].strip()[1:-1]  # убираем внешние скобки
	poly_str = poly_str.split(', ')	# разбиваем полиномы по запятым
	nums = [int(x) for x in lines[1].strip()[1:-1].split(', ')]

	n = len(nums)
	PR = PolynomialRing(F, n, 'x')
	xs = PR.gens()

	# Преобразование полиномов в Sage формат
	polys = []
	for poly in poly_str:
		poly = poly.replace('^', '**')  # перевод в синтаксис sage
		polys.append(PR(poly))

	S = poly_to_tensor(polys, n)
	print(f"S:\n{S}")

	A_rows = matrix(F, n, n)
	for j in range(n):
		# Единичный вектор e_j
		eval_vec = [F(0)] * n
		eval_vec[j] = F(1)
		
		for m in range(n):
			A_rows[j, m] = polys[m](*eval_vec)

	V = Jennrich_algorithm(S, n)
	print(f"V:\n{V}")

	V_cubed = matrix(F, n, n)
	for j in range(n):
		for k in range(n):
			V_cubed[j, k] = pow(V[j, k], 3, Q)
	
	W = V_cubed.inverse() * A_rows
	print(f"W:\n{W}")

	y_vec = vector(F, nums)
	u_cubed = W.transpose().inverse() * y_vec
	inv3 = pow(3, -1, Q - 1)
	u = vector([ui ** inv3 for ui in u_cubed])
	x_sol = V.transpose().inverse() * u
	
	value = 0
	for i, d in enumerate(x_sol):
		value += int(d) * pow(257, i)
	
	blen = (value.bit_length() + 7) // 8
	flag_bytes = value.to_bytes(blen, 'big')
	flag_str = flag_bytes.decode('utf-8', errors='ignore')
		
	print(flag_str)