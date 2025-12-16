# yukari
**SECCON 14**

Cервер пытается собрать систему RSA, а нам необходимо ему помешать. Сервер генерирует простое $p$, получает от пользователя $q$, проверяет его и если оно простое и достаточно большое, то генерирует $e$ и $d$. RSA создается на основе пакета `pycryptodome` функцией `RSA.construct()`.
На CTF было два версии задания: в первой версии нам нужно было сломать сборку RSA 32 раза и $q$ должно быть не менее 1024 бит, во второй нужно слоамть RSA 128 раз и $q$ должно быть ровно 1024 бит. Ниже код более сложной версии:
```
#!/usr/bin/env python3

from Crypto.PublicKey import RSA
from Crypto.Util.number import getPrime, isPrime

with open("flag.txt", "r") as f:
    FLAG = f.read()

for _ in range(128):                 # в легкой версии for _ in range(32):
    p = getPrime(1024)
    print("p =", p)

    q = int(input("q: "))
    assert p != q
    assert q.bit_length() == 1024     # в легкой версии assert q.bit_length() >= 1024
    assert isPrime(q)

    n = p * q
    e = getPrime(64)
    d = pow(e, -1, (p - 1) * (q - 1))

    try:
        cipher = RSA.construct((n, e, d))
    except:
        print("error!")
        continue
    print("key setup successful")
    exit()

print(FLAG)

```

Изучим функцию [`RSA.construct()`](https://github.com/Legrandin/pycryptodome/blob/master/lib/Crypto/PublicKey/RSA.py). Разберемся в каких случаях она выбрасывает исключения:
```
def construct(rsa_components, consistency_check=True):
    ...

    class InputComps(object):
        pass

    input_comps = InputComps()
    for (comp, value) in zip(('n', 'e', 'd', 'p', 'q', 'u'), rsa_components):
        setattr(input_comps, comp, Integer(value))

    n = input_comps.n
    e = input_comps.e
    if not hasattr(input_comps, 'd'):
        key = RsaKey(n=n, e=e)
    else:
        d = input_comps.d
        if hasattr(input_comps, 'q'):
        ...
        else:
            ktot = d * e - 1

            t = ktot
            while t % 2 == 0:
                t //= 2

            spotted = False
            a = Integer(2)
            while not spotted and a < 100:
                k = Integer(t)

                while k < ktot:
                    cand = pow(a, k, n)

                    if cand != 1 and cand != (n - 1) and pow(cand, 2, n) == 1:

                        p = Integer(n).gcd(cand + 1)
                        spotted = True
                        break
                    k *= 2

                a += 2
            if not spotted:
                # не смогли факторизовать n. Факторизация использует недетерминированный алгоритм Рабина. Подробности в "Digitalized Signatures and Public Key Functions as Intractable as Factorization", M. Rabin, 1979
                raise ValueError("Unable to compute factors p and q from exponent d.")

            assert ((n % p) == 0)
            q = n // p

        if hasattr(input_comps, 'u'):
            u = input_comps.u
        else:
            u = p.inverse(q)

        key = RsaKey(n=n, e=e, d=d, p=p, q=q, u=u)

    if consistency_check:

        # Modulus and public exponent must be coprime
        if e <= 1 or e >= n:
            raise ValueError("Invalid RSA public exponent")             #     некорретно выбран e (не наш вариант, тк в коде e = getPrime(64))
        if Integer(n).gcd(e) != 1:
             #   возможно только в случае, если мы передали q, которое не взаимно просто со случайно сгенерированным e, а значит это байпасс проверки isPrime(q)
            raise ValueError("RSA public exponent is not coprime to modulus")      

        # For RSA, modulus must be odd
        if not n & 1:
            raise ValueError("RSA modulus is not odd")   #   возможно только в случае, если мы передали четное q - байпасс isPrime(q)

        if key.has_private():
            if d <= 1 or d >= n:
                raise ValueError("Invalid RSA private exponent")    # не наш вариант, так как d = pow(e, -1, (p - 1) * (q - 1))
            if Integer(n).gcd(d) != 1:
                raise ValueError("RSA private exponent is not coprime to modulus")  # также невозможно из генерации d
            # Modulus must be product of 2 primes
            if p * q != n:
                raise ValueError("RSA factors do not match modulus")   # возможно в случае, если q не простое, значит - байпасс isPrime()
            if test_probable_prime(p) == COMPOSITE:
                raise ValueError("RSA factor p is composite")   # невозможно
            if test_probable_prime(q) == COMPOSITE:
                raise ValueError("RSA factor q is composite")   # аналог isPrime()
            # See Carmichael theorem
            phi = (p - 1) * (q - 1)
            lcm = phi // (p - 1).gcd(q - 1)
            if (e * d % int(lcm)) != 1:
                raise ValueError("Invalid RSA condition")     # невозможно из-за генерации e и d
            if hasattr(key, 'u'):
                # CRT coefficient
                # u = p.inverse(q) потенциальный вектор! Мы можем выбрать q, чтобы u не удовлетворял условию ниже
                if u <= 1 or u >= q:
                    raise ValueError("Invalid RSA component u")
                if (p * u % q) != 1:
                    raise ValueError("Invalid RSA component u with p")

    return key
```

Итак, возможные векторы:
1. Генерировать $q$, такое что алгоритм Рабина не сможет факторизовать $n = p * q$.
2. Байпасс `isPrime()` - сгенерировать составное $q$, которое функция проверки на простоту признает за простое. Данное $q$ достаточно сгенерировать один раз и использовать на всех итерациях проверки.
3. Для каждого $p$ генерировать $q$, такое что $u = p^{-1} \pmod q$ будет больше $q$.

Начнем со второго вектора: оказывается, в более ранних версиях можно было обойти проверку на просто в `isPrime()`. В ней использовался тест Рабина-Миллера с захардкоженными базами проверки. Подробнее можно почитать тут: https://bugs.launchpad.net/pycrypto/+bug/249867
В коде используется версия `pycryptodome 3.23.0`, в которой проверка этот баг исправлен. Теперь в `isPrime()` тест Рабина-Миллера запускается несколько раз, в зависимости от размера входного числа, и использует случайные базы. А после теста Рабина-Миллера запускается тест Лукаса. Таким образом этот вектор будем считать малопригодным к использованию.

Третий вектор может решить легкий вариант задания: будем генерировать $q$ вида $k * p + 1$ и проверять, что число простое, достаточно большое и ломает RSA. Конкретно, оно ломает проверку $u$, так как в таком случае $u = 1$ ($p = 1 \pmod {k * p + 1}$). Скрипт для решения данным методом [solve_brute.py](https://github.com/andreika47/Quiet-CTF/blob/main/yukari/solve_brute.py)

Для сложного вариант данный способ не подходит, так как он генерирует $q$ длины большей чем 1024 бита. Изучим подробнее алгоритма Рабина и попробуем найти условия, при которых он не сможет факторизовать $n$. Алгоритм Рабина основывается на идее поиска нетривиального квадратного корня $x^2 = 1 \pmod n$, $x != 1$, $x != -1$. Тогда:
$x^2 - 1 = (x + 1) * (x - 1) \pmod n$
А так как $n$ имеет ровно два нетривиальных делителя, то $p = x + 1$, $q = x - 1$.
Основная проблема алгоритма в том, как искать подобный нетривиальный корень. В коде `RSA.construct` перебирается параметр `a` от `2` до `100` с шагом `2` и на каждой итерации проверяется кандидат на нетривиальный корень вида $a^{r * t} \pmod n$, где $k = 1, 2, 4, ..., 2^s$, а $s$ и $t$ вычисляются как $d * e - 1 = t * 2^s$. Тогда, если $p$ и $q$ будут иметь схожую структуру, а именно если они их символы Лежандра $\left(\frac{a}{p}\right)$ и $\left(\frac{a}{q}\right)$ будут совпадать, то алгоритма Рабина будет чаще получать тривиальные корни и не сможет факторизовать $n$. Теперь нужно понять, как генерировать $q$ схожую по структуре с $p$.

Рассмотрим 2 случая:
1. $p = 1 \pmod 4$
2. $p = 3 \pmod 4$

В первом случае нам важно $p-1$ будет иметь степень $2$ в разложении на простые, и нам важно, чтобы $q-1$ имело такую же 2-адическую структуру. По теореме Ферма-Эйлера, любое простое число вида $p = 4m + 1$ можно представить в виде суммы двух квадратов. Попробуем просто генерировать такие числа, проверять что они простые и удовлетворяют нашим требованиям по размеру. Чтобы они были близки к $p$ можно разложить $p$ на сумму квадратов $p = a^2 + b^2$ и прибавлять некоторую константу к $a$ и $b$. В какой-то момент мы получим простое число, которое удволетворяет нашим требование и даже "ломает" алгоритм Рабина. Но, если $p$ сравнимо с $1$ для более высоких степеней двойки, например, $p = 1 \pmod 8$, то мы можем получить $q$, для которого найдется $a$ с символом Лежандра $\left(\frac{a}{q}\right)$ отличном от $\left(\frac{a}{p}\right)$. Поэтому, нам нужно рассматривать дополнительные случаи, в текущей задаче хватило дополнительно расссмотреть $p = 1 \pmod 16$ и $p = 1 \pmod 8$. Разложение на сумму квадратов для $p = 1 \pmod 4$ можно свести к разложению $p$ в круговом поле с соответсвующей характеристикой. Для примера возьмем $p = 1 \pmod 8$: в этом случае $p$ можно разложить на композицию 4 простых иделов в круговом поле с характеристикой 8. Попробуем аналогично получить $q$ перебирая возможные комбинации идеалов, норма которой должна быть простым числом. Таким образом мы получим новое простое число $q = 1 \pmod 8$. Остается проверить, что такая пара $p$ и $q$ "ломает" генерацию RSA.

Для случая $p = 3 \pmod 4$ подобного разложения пока нет, поэтому просто перебираем простые, прибавляя к $p$ некоторую константу. И в первом, и в этом случае использовалась одна и та же константа: НОК от всех четных чисел от 2 до 100 - чтобы в шаге содержалась приличная степень двойки и много простых чисел. Такая константа позволяет чаще получать простые числа, сохраняя остаток от деления на 4.

Полный код решения: [solve.py](https://github.com/andreika47/Quiet-CTF/blob/main/yukari/solve.py)

#crypto #rsa #number_theory

