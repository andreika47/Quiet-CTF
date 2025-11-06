from sage.all import *
from collections import queue

def calc_period(lfsr_poly, n):
    return "неизвестно"

def analyze_lfsr(n, mask):
    print(f"\n================\nМаска: {mask}, для регистра из {n} бит\n================\n")
    poly_bits = []

    for i in range(n):
        if mask & (1 << i):
            poly_bits.append(i)

    B = BooleanPolynomialRing(n, ['x%d' % i for i in range(n)])
    xs = B.gens()

    poly_terms = []
    gates = []
    for bit_pos in poly_bits:
        poly_terms.append(xs[bit_pos])
        gates.append(bit_pos + 1)

    lfsr_poly = sum(poly_terms)
    print(f"   P(x) = {lfsr_poly}")
    
    is_primitive = False
    max_period = 2**(n - 1)

    if len(gates) % 2 == 0 and gcd(gates) == 1:
        is_primitive = True

    add = "" if is_primitive else "НЕ "
    period = max_period if is_primitive else calc_period(lfsr_poly, n)
    
    print(f"\nДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:")
    print(f"   • Полином {add}примитивен")
    print(f"   • Период: {period}")
    print(f"   • Участвующие биты: {sorted(poly_bits)}")
    
    return {
        'poly': lfsr_poly,
        'is_primitive': is_primitive,
        'max_possible_period': max_period
    }

if __name__ == "__main__":
    Ns = [14, 32, 24, 48, 8, 8, 8, 8, 10]
    MASKS = [0x7a7, 0xcfdf1bcf, 0xb9ca5b, 0x83c7efefc783, 0x27, 0x65, 0x63, 0x2b, 0x243]
    
    for i in range(len(Ns)):
        analyze_lfsr(Ns[i], MASKS[i])



# def lfsr_cycle_length(n, mask, initial_state=1, max_steps=None):
#     """
#     Вычисляет длину цикла LFSR
    
#     Args:
#         n: длина LFSR в битах
#         mask: маска обратной связи
#         initial_state: начальное состояние (не должно быть 0)
#         max_steps: максимальное количество шагов для проверки
    
#     Returns:
#         tuple: (длина_цикла, является_ли_максимальной, все_состояния)
#     """
#     if max_steps is None:
#         max_steps = (1 << n)
    
#     if initial_state == 0:
#         initial_state = 1  # Нулевое состояние зацикливается
    
#     state = initial_state
#     states_seen = {}
#     states_list = []
#     step = 0
    
#     while state not in states_seen and step < max_steps:
#         states_seen[state] = step
#         states_list.append(state)
        
#         # Вычисляем следующий бит обратной связи
#         feedback = (state & mask).bit_count() & 1
#         # Сдвигаем и добавляем новый бит
#         state = (state >> 1) | (feedback << (n - 1))
#         step += 1
        
#         # Проверяем на нулевое состояние (зацикливание)
#         if state == 0:
#             break
    
#     if state in states_seen:
#         cycle_start = states_seen[state]
#         cycle_length = step - cycle_start
#         max_possible = (1 << n) - 1
#         is_maximal = (cycle_length == max_possible)
        
#         return cycle_length, is_maximal, states_list
#     else:
#         return step, False, states_list

# def analyze_mask(n, mask, mask_name=""):
#     """Анализирует конкретную маску"""
#     print(f"\n{'='*60}")
#     print(f"Анализ маски {mask_name}: 0x{mask:x} (длина LFSR: {n} бит)")
#     print(f"{'='*60}")
    
#     cycle_len, is_maximal, states = lfsr_cycle_length(n, mask)
#     max_possible = (1 << n) - 1
    
#     print(f"Длина цикла: {cycle_len}")
#     print(f"Максимально возможная длина: {max_possible}")
    
#     # Анализ периода для разных начальных состояний
#     print(f"\nПроверка различных начальных состояний:")
#     test_states = [1, (1 << (n-1)), (1 << (n//2)) | 1, (1 << n) - 1]
    
#     for init_state in test_states:
#         if init_state >= (1 << n):
#             continue
#         test_len, test_max, _ = lfsr_cycle_length(n, mask, init_state)
#         print(f"  Начальное состояние 0x{init_state:x}: длина цикла = {test_len}")
    
#     return cycle_len, is_maximal

# def polynomial_analysis(n, mask):
#     """Анализирует полиномиальные свойства маски"""
#     print(f"\nПолиномиальный анализ для маски 0x{mask:x}:")
    
#     # Преобразуем маску в полиномиальную форму
#     polynomial_terms = []
#     for bit in range(n):
#         if (mask >> bit) & 1:
#             if bit == 0:
#                 polynomial_terms.append("1")
#             else:
#                 polynomial_terms.append(f"x^{bit}")
    
#     poly_str = " + ".join(polynomial_terms) + f" + x^{n}"
#     print(f"Полином: {poly_str}")
    
#     # cycle_len, is_maximal, _ = lfsr_cycle_length(n, mask)
#     is_prime_period = period.is_prime()
    
#     # return is_prime_period
#     return is_prime_period

# def comprehensive_analysis():
#     """Комплексный анализ всех LFSR"""
#     Ns = [14, 32, 24, 48, 8, 8, 8, 8, 10]
#     MASKS = [0x7a7, 0xcfdf1bcf, 0xb9ca5b, 0x83c7efefc783, 0x27, 0x65, 0x63, 0x2b, 0x243]
    
#     print("КОМПЛЕКСНЫЙ АНАЛИЗ LFSR СИСТЕМЫ")
#     print("=" * 80)
    
#     total_bits = sum(Ns)
#     print(f"Общая длина всех LFSR: {total_bits} бит")
#     print(f"Общее пространство состояний: 2^{total_bits} = {1 << total_bits}")
    
#     results = []
    
#     for i, (n, mask) in enumerate(zip(Ns, MASKS)):
#         print(f"\n{'#'*50}")
#         print(f"LFSR {i} (длина {n} бит, маска 0x{mask:x})")
#         print(f"{'#'*50}")
        
#         # Основной анализ
#         # cycle_len, is_maximal = analyze_mask(n, mask)
        
#         # Полиномиальный анализ
#         is_primitive = polynomial_analysis(n, mask)
        
#         results.append({
#             'lfsr': i,
#             'length': n,
#             'mask': mask,
#             # 'cycle_length': cycle_len,
#             'is_primitive': is_primitive
#         })
    
#     # Сводная таблица
#     print(f"\n{'='*80}")
#     print("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
#     # print(f"{'='*80}")
#     # print(f"{'LFSR':<6} {'Длина':<8} {'Маска':<15} {'Цикл':<15} {'Примитивность':<15}")
#     # print(f"{'-'*80}")
    
#     # for res in results:
#     #     status = "ДА" if res['is_primitive'] else "НЕТ"
#     #     print(f"{res['lfsr']:<6} {res['length']:<8} 0x{res['mask']:<13x} {res['cycle_length']:<15} {status:<15}")
    
#     # Анализ малых LFSR
#     small_lfsrs = [res for res in results if res['length'] <= 8]
#     if small_lfsrs:
#         print(f"\n⚠️  Обнаружены малые LFSR (<= 8 бит):")
#         for lfsr in small_lfsrs:
#             # print(f"   LFSR {lfsr['lfsr']}: {lfsr['length']} бит, период = {lfsr['cycle_length']}")
#             print(f"   LFSR {lfsr['lfsr']}: {lfsr['length']} бит")
#         print("   Эти LFSR могут быть уязвимы для brute-force атак!")
    
#     return results

# if __name__ == "__main__":
#     # Запуск комплексного анализа
#     results = comprehensive_analysis()
    