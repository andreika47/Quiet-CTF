# Revenge of the Sith
**LakeCTF 2025**

Усложненная версия [Attack of the Clones](https://github.com/andreika47/Quiet-CTF/tree/main/Attack%20of%20the%20Clones):
* Сообщение теперь разбито на блоки
* Каждый блок шифруется отдельно со случайно сгенерированными параметрами шума
* Публичный ключ всего один для всего сообщения
* Новые значения параметров `q = 251`, `n = 16`, `k = 2` (выглядит значительно меньше)

Секретный ключ $s$ - это вектор полиномов с коэффициентами ${-1, 0, 1}$:<br>
$s \in R^k$, где $R = \mathbb{F}\_q[x]/(x^n + 1)$
Публичный ключ генерируется как:
$t = A * s + e$, где $e$ - вектор с шумом.

Шифрование каждого блока $m_b$ сообщения $m$ происходит по следующему алгоритму:
1. Генерируются случайные параметры: $r_b \in R^k$, $e_{1,b} \in R^k$, $e_{2,b} \in R$
2. Вычисляется блок шифртекста:
$u_b = A^T * r_b + e_{1,b}$
$v_b = t * r_b + e_{2,b} + \tilde{m}\_b$, где $\tilde{m}\_b = m_b * \lfloor(q+1)/2\rfloor \mod q$

Хотя в отличие от [Attack of the Clones](https://github.com/andreika47/Quiet-CTF/tree/main/Attack%20of%20the%20Clones) для каждого блока сообщения используются разные случайные параметры, система имеет следующие проблемы:
1. $n=16$ означает, что в полиноме $r_b$ всего 16 коэффициентов
2. $k=2$ означает, что вес полинома $r_b$ равен 2
Таким образом пространство перебора $r_b$: $(\binom{16}{2} \cdot 2^2)62 = 480^2 = 230400$. Для каждого блока шифртекста $u_b$ будем перебирать все возможные $r_b$. Для каждого кандидата $r_b$ будем восстанавливать $e_{1,b} = u_b - A^T * r_b$. Проверим, что $e_{1,b}$ имеет правильную структуру:
```
def check_error(e):
	for poly in e:
		if not all(coeff in [-1, 0, 1] for coeff in vector(poly).lift_centered()):
			return False
	return True
```
Далее вычисляем блок открытого текста:
$m_b = v_b - t * r_b = e_{2,b} + \tilde{m}\_b$
Поскольку $e_{2,b}$ мал (вес 2), а $\tilde{m}\_b$ принимает значения либо 0, либо $\lfloor(q+1)/2\rfloor$, округляем найденные значения:
```
def round_q(m):
	return [0 if abs(coeff) < q/4 else 1 for coeff in vector(m).lift_centered()]
```

Полный код решения: [solve.py](https://github.com/andreika47/Quiet-CTF/blob/main/Revenge%20of%20the%20Sith/solve.py)

#crypto #kyber #general_algebra #computer_algebra