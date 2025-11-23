# SuanP01y
**RCTF 2025**

Из кода задания chall.sage:
```
from sage.all import GF, ZZ, sample, gcd, PolynomialRing
from Crypto.Cipher import AES
from hashlib import md5
import os

r, d = 16381, 41
R.<x> = PolynomialRing(GF(2))
S.<X> = R.quo(x^r - 1)

def suan_p01y(nt, db):
    return sum(x^i for i in set(sample(range(db+1), nt)))

while True:
    t = [suan_p01y(d, r//3) for _ in range(2)]
    if gcd(t[0], t[1]) != 1:
        continue
    h = [(ti * X^ZZ.random_element(r)) for ti in t]
    if h[0].is_unit():
        break

with open("output.txt", "w") as f:
    f.write(f"hint = {h[1] / h[0]}\n")
    f.write(
        AES.new(
            key=md5(str(h[0]).encode()).digest(),
            nonce=b"suanp01y",
            mode=AES.MODE_CTR
        ).encrypt(os.environ.get("FLAG", "RCTF{fake_flag}").encode()).hex()
    )

```

мы имеем дело с криптосистемой, основанной на кольце полиномов над полем $GF(2)$ по модулю $x^r - 1$, где $r = 16381$. Основные вычисления происходят в факторкольце $S = GF(2)[x]/(x^r - 1)$, а нам в качестве подсказки дан результат деления двух некоторых полиномов: $hint = {h_1}/{h_0}$.<br>
Полиномы $h_0$, $h_1$ получены из полиномов $t_0$, $t_1$, соответственно, умножением на некоторые $X^{r_0}$, $X^{r_1}$. По сути данное умножение является циклическим свдигом коэффициентов полинома. Таким образом:<br>
$$hint = {h_1}/{h_0} = {t_1 * X^{r_1}}/{t_0 * X^{r_0}} = {t_1}/{t_0} * X^{r_1 - k_0}$$<br>
Умножив левую и правую части на ${t_0}$ получим:<br>
$${t_0} * hint = {t_1} * X^{r_1 - r_0}$$<br>
Из построения полиномв $t_0$ и $t_1$ видно, что они имеют вес 41 ненулевой коэффииент и индексы всех эти коэффициентов находятся в интервале $[0; r/3]$.<br>
Основная идея решения: восстановить $t_0$, $t_1$ с помощью расширенного алгоритма Евклида. Для некоторых полиномов $a(x), b(x) \\in GF(2)[x]$ расширенный алгоритм Евклдиа позволяет найти соотношение<br>
$$j_i(x)a(x) + k_i(x)b(x) = l_i(x)$$,<br>
где:<br>
* $l_i(x)$ - полином остатков,
* $j_i(x)$, $k_i(x)$ - коэффициенты Безу;

Данное соотношение имеют похожую форму, что и ${t_0} * hint = {t_1} * X^{r_1 - r_0}$. Взяв $a(x) = x^r - 1$, $b(x) = hint$ найдем $k_i(x)$, $l_i(x)$ наименьшего веса, такие что выполняется условие:<br>
$$l_i(x) \equiv k_i(x) * hint \pmod a(x)$$<br>
На одном из шагов мы получим:<br>
$${k_i}(x) * hint = {l_i}(x)$$,<br>
где:
* ${k_i}(x) = t_0$,
* ${l_i}(x) = t_1 * X^{r_1 - r_0}$;

#crypto #polynomial #linear_algebra
