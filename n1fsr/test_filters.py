import numpy as np
from collections import Counter

# Константы из задания
Filters = [
    237861018962211057901759878514586912107,
    69474900172976843852504521249820447513188207961992185137442753975916133181030,
    28448620439946980695145546319125628439828158154718599921182092785732019632576,
    16097126481514198260930631821805544393127389525416543962503447728744965087216,
    7283664602255916497455724627182983825601943018950061893835110648753003906240,
    55629484047984633706625341811769132818865100775829362141410613259552042519543,
    4239659866847353140850509664106411172999885587987448627237497059999417835603,
    85329496204666590697103243138676879057056393527749323760467772833635713704461
]

blur = lambda x, i: (Filters[i] >> x) & 1

def test_nonlinearity_filter(i):
    """Тестирует нелинейность фильтра i"""
    print(f"\n=== Тестирование фильтра {i} ===")
    
    # Преобразуем фильтр в функцию f: {0,1}^8 -> {0,1}
    filter_func = {}
    for x in range(256):
        filter_func[x] = blur(x, i)
    
    # Тест 1: Проверка сбалансированности
    outputs = [filter_func[x] for x in range(256)]
    ones_count = sum(outputs)
    zeros_count = 256 - ones_count
    print(f"Сбалансированность: 0={zeros_count}, 1={ones_count}")
    
    # Тест 2: Проверка нелинейности (Walsh-Hadamard transform)
    def walsh_hadamard(f):
        """Вычисляет преобразование Уолша-Адамара"""
        F = np.zeros(256, dtype=int)
        for a in range(256):  # a - линейная маска
            sum_val = 0
            for x in range(256):
                # (-1)^(f(x) + a·x)
                dot_product = 0
                for bit in range(8):
                    if (a >> bit) & 1 and (x >> bit) & 1:
                        dot_product ^= 1
                value = f[x] ^ dot_product
                sum_val += 1 if value == 0 else -1
            F[a] = sum_val
        return F
    
    F = walsh_hadamard(filter_func)
    
    # Находим максимальное абсолютное значение (нелинейность)
    max_abs_F = np.max(np.abs(F))
    nonlinearity = (256 - max_abs_F) // 2
    print(f"Нелинейность: {nonlinearity} (макс |F(a)| = {max_abs_F})")
    
    # Тест 3: Проверка на аффинность
    is_affine = max_abs_F == 256
    print(f"Является аффинной: {is_affine}")
    
    # Тест 4: Корреляционный иммунитет (упрощенный)
    def correlation_immunity(f):
        """Проверяет корреляционный иммунитет 1-го порядка"""
        for bit_pos in range(8):
            # Проверяем, зависит ли f от бита bit_pos
            dependent = False
            for x in range(256):
                x_flipped = x ^ (1 << bit_pos)
                if f[x] != f[x_flipped]:
                    dependent = True
                    break
            if not dependent:
                return False, bit_pos
        return True, None
    
    corr_immune, independent_bit = correlation_immunity(filter_func)
    print(f"Корреляционный иммунитет 1-го порядка: {corr_immune}")
    if not corr_immune:
        print(f"  Независим от бита {independent_bit}")
    
    # Тест 5: Нелинейные свойства
    nonlinear_coeff = max_abs_F / 256
    print(f"Коэффициент нелинейности: {nonlinear_coeff:.4f}")
    
    return nonlinearity, nonlinear_coeff

def test_algebraic_degree(i):
    """Оценивает алгебраическую степень фильтра"""
    print(f"\n--- Алгебраическая степень фильтра {i} ---")
    
    filter_func = {}
    for x in range(256):
        filter_func[x] = blur(x, i)
    
    # Преобразуем в алгебраическую нормальную форму (АНФ)
    def anf_transform(f):
        """Вычисляет АНФ с помощью преобразования Мёбиуса"""
        anf = f.copy()
        # Преобразование Мёбиуса
        for i in range(8):
            step = 1 << i
            for j in range(0, 256, step << 1):
                for k in range(j, j + step):
                    anf[k + step] ^= anf[k]
        return anf
    
    anf = anf_transform([filter_func[x] for x in range(256)])
    
    # Находим максимальную степень
    max_degree = 0
    for x in range(256):
        if anf[x] == 1:
            degree = bin(x).count('1')  # Количество единиц в двоичном представлении
            if degree > max_degree:
                max_degree = degree
    
    print(f"Алгебраическая степень: {max_degree}")
    
    # Анализ распределения мономов по степеням
    degree_dist = Counter()
    for x in range(256):
        if anf[x] == 1:
            degree = bin(x).count('1')
            degree_dist[degree] += 1
    
    print("Распределение мономов по степеням:")
    for deg in sorted(degree_dist.keys()):
        print(f"  Степень {deg}: {degree_dist[deg]} мономов")
    
    return max_degree

def analyze_all_filters():
    """Анализирует все фильтры"""
    print("=" * 60)
    print("АНАЛИЗ ФИЛЬТРОВ")
    print("=" * 60)
    
    results = []
    
    for i in range(len(Filters)):
        nonlinearity, nonlinear_coeff = test_nonlinearity_filter(i)
        algebraic_degree = test_algebraic_degree(i)
        
        results.append({
            'filter': i,
            'nonlinearity': nonlinearity,
            'nonlinear_coeff': nonlinear_coeff,
            'algebraic_degree': algebraic_degree
        })
        
        print("\n" + "=" * 50)
    
    # Сводный анализ
    print("\n" + "=" * 60)
    print("СВОДНЫЙ АНАЛИЗ ВСЕХ ФИЛЬТРОВ")
    print("=" * 60)
    
    for res in results:
        print(f"Фильтр {res['filter']}:")
        print(f"  Нелинейность: {res['nonlinearity']}")
        print(f"  Коэф. нелинейности: {res['nonlinear_coeff']:.4f}")
        print(f"  Алгебраическая степень: {res['algebraic_degree']}")

if __name__ == "__main__":
    # Запускаем полный анализ
    analyze_all_filters()
    