from pwn import *
from Crypto.Util.number import isPrime, getPrime
from Crypto.PublicKey import RSA

HOST = 'yukari.seccon.games'
PORT = 15809

def solve():
    r = remote(HOST, PORT)

    for i in range(32):
        print(f"[*] Round {i+1}/32")

        r.recvuntil(b"p = ")
        p = int(r.recvline().strip())
        print(f"\t{p = }")

        k = 2
        while True:
            q = k * p + 1
            if isPrime(q) and q.bit_length() >= 1024:
                n = p * q
                e = getPrime(64)
                d = pow(e, -1, (p - 1) * (q - 1))

                try:
                    cipher = RSA.construct((n, e, d))
                except Exception as ex:
                    print(f"[ERROR]: {ex}")
                    break
            k += 1
            
        r.sendlineafter(b"q: ", str(q).encode())
        result = r.recvline()
        if b"error!" in result:
            print("\tSuccess!")
        elif b"key setup successful" in result:
            print(f"\tFailed!\n\t{p = }\n\t{q = }")
            return
        else:
            print(f"\tUnknown response: {result}")

    print(r.recvall().decode())

if __name__ == "__main__":
    solve()
