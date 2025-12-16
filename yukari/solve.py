from pwn import *
from Crypto.Util.number import isPrime, getPrime
from Crypto.PublicKey import RSA
from sage.all import *
import itertools

HOST = 'yukari-infinity.seccon.games'
PORT = 13910
K8 = CyclotomicField(8)
K16 = CyclotomicField(16)

def get_q_1_16(p, step):
	facs = K16.fractional_ideal(p).factor()
	ideal = facs[0][0]
	pi = ideal.gens_reduced()[0]
	pi_list = pi.list()
	perms = itertools.permutations(range(len(pi_list)))
	for ids in perms:
		new_pid = [u0 + v * step for u0, v in zip(pi_list, ids)]
		new_pi = K16(new_pid)
		q = int(new_pi.norm())
		if isPrime(q):
			if test(p, q):
				return q

	return None

def get_q_1_8(p, step):
	facs = K8.fractional_ideal(p).factor()
	ideal = facs[0][0]
	pi = ideal.gens_reduced()[0]
	pi_list = pi.list()
	for ids in itertools.product(range(len(pi_list) * 2), repeat=len(pi_list)):
		new_pid = [u0 + v * step for u0, v in zip(pi_list, ids)]
		new_pi = K8(new_pid)
		q = int(new_pi.norm())
		if q.bit_length() == 1024:
			if isPrime(q):
				if test(p, q):
					return q

	return None

def get_q_1_4(p, step):
	a, b = two_squares(p)
	for i in range(100):
		for j in range(100):
			if i > 0 or j > 0:
				a1 = a + i * step
				b1 = b + j * step
				q = a1 ** 2 + b1 ** 2
				if q.bit_length() == 1024:
					if isPrime(q):
						if test(p, q):
							return q

def get_q_3_4(p, step):
	q = p + step
	for _ in range(1000):
		if q.bit_length() == 1024:
			if isPrime(q):
				if test(p, q):
					return q
		else:
			print(f"WRONG LEN: {q.bit_length()}")

		q += step

	return None

def test(p, q):
	if p != q:
		n = p * q
		e = getPrime(64)
		d = pow(e, -1, (p - 1) * (q - 1))

		ktot = d * e - 1
		# print(f"{ktot = }")
        t = ktot
        while t % 2 == 0:
            t //= 2
        spotted = False
        a = Integer(2)
        # print(f"{t = }")
        while not spotted and a < 100:
            k = Integer(t)
            # print(f"\t{k = }")
            while k < ktot:
                cand = pow(a, k, n)
                # print(f"\t\t{ = }")
                if cand != 1 and cand != (n - 1) and pow(cand, 2, n) == 1:
                    p_cand = Integer(n).gcd(cand + 1)
                    spotted = True
                    break
                k *= 2
            a += 2

        if spotted:
        	print(f"Found {p_cand = }")
        	return False
        else:
            print("Unable to compute factors p and q from exponent d.")
            return True

	return False

def solve():
	retry = True
	start_step = 1
	for i in range(2, 100, 2):
	    start_step = lcm(i, start_step)

	while retry:
		retry = False
		r = remote(HOST, PORT)

		for i in range(128):
			print(f"[*] Round {i+1}/128")
			q = None

			r.recvuntil(b"p = ")
			p = int(r.recvline().strip())
			step = start_step
			if p % 16 == 1:
				while q is None:
					q = get_q_1_16(p, step)
					step += 1
			elif p % 8 == 1:
				step = start_step
				while q is None:
					q = get_q_1_8(p, step)
					step += 1

				print(f"{q = }")
			elif p % 4 == 1:
				q = get_q_1_4(p, step)
			elif p % 4 == 3:
				q = get_q_3_4(p, step)

			if q:
				r.sendlineafter(b"q: ", str(q).encode())
				result = r.recvline()
				if b"error!" in result:
					print("\tSuccess!")
				elif b"key setup successful" in result:
					print(f"\tFailed! {p % 16 = }")
					retry = True
					break
				else:
					print(f"\tFailed! {p % 16 = }")
					print(f"\tUnknown response: {result}")
					print(r.recvall().decode())
					retry = True
					break
			else:
				retry = True
				break

		if retry:
			r.close()
		else:
			print(r.recvall().decode())

if __name__ == "__main__":
	solve()