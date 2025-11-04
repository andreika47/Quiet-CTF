import os, secrets, signal
from collections import deque
from math import ceil, log2, gcd

def hash(params, msg):
	a, b, c, m, x = params
	for byte in msg:
		for bit in f'{byte:08b}':
			x = ((x * a + b + int(bit)) ^ c) % m
	return x

def hash_bits(params, bits):
	a, b, c, m, x = params
	for bit in bits:
		x = ((x * a + b + int(bit)) ^ c) % m
	return x

def forward_step(x_init, nbit, steps, valid_paths):
	""" Реализация обратного прохода:
	генерируем все возможные состояния после 'steps' шагов хэширования для всех возможных путей 'valid_paths'
	"""
	a, b, c, m = GLOBAL_A, GLOBAL_B, GLOBAL_C, GLOBAL_M
	mod_mask = (1 << nbit) - 1
	n_choices = len(valid_paths)
	deque_states = deque()
	deque_states.append((x_init & mod_mask, []))
	while deque_states:
		state, path = deque_states.popleft()
		if len(path) == steps:
			yield (state, path)
			continue
		for idx in range(n_choices):
			new_state = state
			new_path = path + [idx]
			for bit in valid_paths[idx]:
				new_state = ((new_state * a + b + bit) ^ c) & mod_mask
			deque_states.append((new_state, new_path))
			
def backward_step(state_target, nbit, steps, valid_paths):
	""" Реализация обратного прохода:
	генерируем все возможные состояния до 'steps' шагов хэширования для всех возможных путей 'valid_paths'
	"""
	a, b, c, m = GLOBAL_A, GLOBAL_B, GLOBAL_C, GLOBAL_M
	mod_mask = (1 << nbit) - 1
	
	# кэшируем найденные обратные по модулю
	if nbit not in GLOBAL_A_INV_CACHE:
		GLOBAL_A_INV_CACHE[nbit] = pow(a, -1, 1 << nbit)
	a_inv = GLOBAL_A_INV_CACHE[nbit]
	
	n_choices = len(valid_paths)
	deque_states = deque()
	deque_states.append((state_target & mod_mask, []))
	while deque_states:
		state, path = deque_states.popleft()
		if len(path) == steps:
			yield (state, path)
			continue
		for idx in range(n_choices):
			new_state = state
			new_path = [idx] + path
			for bit in reversed(valid_paths[idx]):
				'''
				Делаем "обратное" хэширование:
				x_i-1 = (((x_i ^ c) - msg_i - b) * a_inv) mod 2^128

				в конце прибавляем m, чтобы число не было отрицательным и Python меньше мучался с побитовыми операциями
				'''
				new_state = (((new_state ^ c) - b - bit) * a_inv + m) & mod_mask
			deque_states.append((new_state, new_path))

def find_lsb_path_mitm(x_init, nbit, steps, valid_paths=None, findall=True):
	global GLOBAL_TARGET
	
	target = GLOBAL_TARGET
	
	# Инициализируем бинарный поиск
	if valid_paths is None:
		valid_paths = [[0], [1]]
	
	k = steps // 2
	r = steps - k
	
	print(f"[MITM] Forward: {k} steps, Backward: {r} steps (total: {steps}), {len(valid_paths)} choices, length of path segment: {len(valid_paths[0])}")
	
	'''
	Прямой проход: вычисляем все возможные состояния после k шагов
	Делаем отображение состояния в список из путей, где путь - это возможные биты сообщения, дающие искомы хэш для текущей длины коллизии
	'''
	forward = {}
	
	for state, path in forward_step(x_init, nbit, k, valid_paths):
		path_indices = tuple(path)
		if state not in forward:
			forward[state] = []
		forward[state].append(path_indices)
	print(f"[MITM] Forward phase done: {len(forward)} unique states")
	
	# Делаем обратный проход и ищем коллизии
	results = []
	for state, path_indices in backward_step(target, nbit, r, valid_paths):
		if state in forward:
			# Восстанавливаем полный путь
			for path_indices1 in forward[state]:
				full_path_indices = list(path_indices1) + list(path_indices)
				full_path = []
				for idx in full_path_indices:
					full_path.extend(valid_paths[idx])
				if findall:
					results.append(full_path)
				else:
					return full_path
	if findall:
		return results

def attack(params, target, nbits):
	a, b, c, m, x_init = params
	COLLISION_STEP = 32
	OPT_CIRCLE_PATHS = 16  # оптимальное число возможных путей для работы (найдено эмпирическим путем)
	
	step_size = COLLISION_STEP + 8	# на первом этапе посчитаем хэш для состояний на 1 байт дальше, чем желаемое сообщение с LSB совпадающими с target
	final_path = []
	valid_circle_paths = [[0], [1]]
	cur_target = x_init

	for stage in range(nbits // COLLISION_STEP):
		collided_bits = (stage + 1) * COLLISION_STEP
		print(f"\n[Stage {stage+1}] Colliding on next {COLLISION_STEP} bits with {step_size = } ({collided_bits = })...")
		mask = (1 << collided_bits) - 1

		for try_step_size in range(step_size, step_size + 4):
			path = find_lsb_path_mitm(cur_target, collided_bits, try_step_size, valid_circle_paths, findall=False)
			if path:
				break

		if not path:
			print(f'⚠️  No path found in stage {stage+1} with step_size={step_size}, aborting...')
			break

		final_path.extend(path)
		print(f'[+] Found path of length {len(path)} bits in stage {stage+1}, total {len(final_path)} bits')
		cur_target = hash_bits(params, final_path)

		assert cur_target & mask == target & mask, f"Intermediate target mismatch at stage {stage+1}"

		if collided_bits >= nbits:
			print(f'[+] Reached full {nbits} bits collision, done!')
			break
		
		for try_step_size in range(step_size, step_size + 4):
			print(f'💡 Searching for circle paths with step_size={try_step_size}...')

			new_valid_circle_paths = find_lsb_path_mitm(target, collided_bits, try_step_size, valid_circle_paths, findall=True)
			if new_valid_circle_paths and len(new_valid_circle_paths) >= OPT_CIRCLE_PATHS:
				print(f'[+] Found {len(new_valid_circle_paths)} circle paths in stage {stage+1}')
				break


		if not new_valid_circle_paths or len(new_valid_circle_paths) < OPT_CIRCLE_PATHS:
			print(f'[-] Could not find enough circle paths in stage {stage+1}, stopping here.')
			break

		valid_circle_paths = new_valid_circle_paths[:OPT_CIRCLE_PATHS]
		step_size = 8

	bytes_msg = bytearray()
	# преобразуем полученыне биты пути в исходное сообщение msg
	for i in range(0, len(final_path), 8):
		byte = 0
		for j in range(8):
			if i + j < len(final_path):
				byte = (byte << 1) | final_path[i + j]
			else:
				byte = (byte << 1)
		bytes_msg.append(byte)

	return bytes_msg


nbits = 128
rand = lambda: secrets.randbits(nbits)
print('⚙️', params := (rand() | 1, rand(), rand(), 2 ** nbits, rand()))
print('🎯', target := rand())

GLOBAL_A, GLOBAL_B, GLOBAL_C, GLOBAL_M, x_init = params
GLOBAL_TARGET = target
GLOBAL_A_INV_CACHE = {}  # будем кэшировать найденные обратные по модулю

message = attack(params, target, nbits)
assert hash(params, message) == target, '❌'
print('🚩', os.getenv("FLAG"))