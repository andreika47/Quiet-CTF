FLAG = ZZ.from_bytes(os.getenvb(b"FLAG", b"n1ctf{.*}")[6:-1]).digits(257)
F, n = GF(257), len(FLAG)
U, T = [random_matrix(F, n) for _ in ':)']
enc = lambda x: (x * U).apply_map(lambda c: c^3) * T
print(enc(vector(F[",".join(f"x{i}" for i in range(n))].gens())))
print(enc(vector(F, FLAG)))
