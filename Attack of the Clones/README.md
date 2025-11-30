# Attack of the Clones
**LakeCTF 2025**

Задание похоже на схему Kyber, где одно и то же сообщение зашифровано дважды с разными публичными ключами, но с одинаковыми случайными параметрами $r$, $e_1$, $e_2$.
Даны:
* Два публичных ключа: $(A_2, t_1)$ и $(A_2, t_2)$
* Два шифротекста: $(u_1, v_1)$ и $(u_2, v_2)$
* Параметры: `q = 3329`, `n = 512`, `k = 4`<br>
<br>
Из кода генерации ключей следует:<br>
$u_1 = {A_1}^T * r + e_1$<br>
$v_1 = t_1 * r + e_2 + m$<br>
$u_2 = {A_2}^T * r + e_1$<br>
$v_2 = t_2 * r + e_2 + m$<br>
<br>
Поскольку в обоих шифрованиях используются одинаковые $r$, $e_1$, $e_2$, мы можем вычесть одно уравнение из другого и избавится от $e_1$:<br>
$u_1 - u_2 = ({A_1}^T - {A_2}^T) * r$<br>
Из уравнения выше получаем:<br>
$r = ({A_1}^T - {A_2}^T)^{-1} * (u_1 - u_2)<br>
Используя найденное $r$ вычислим<br>
$v_1 - t_1 * r = (t_1 * r + e_2 + m) - t_1 * r = e_2 + m$<br>
Поскольку $e_2$ - дает совсем небольшой шум, а $m$ принимает значения либо 0, либо $(q+1)/2$, мы можем округлить результат:
* Если коэффициент близок к $0$, то берем нулевой бит
* Если коэффициент близок к $(q+1)/2$, то берем единичный бит<br>
Код решения меньше кода задания:<br>
```
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
```

#crypto #kyber #general_algebra #computer_algebra
