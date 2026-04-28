# BaseCamp
**AlfaCTF 2026**

Дан сервис - база курсов, каждый из которых состоит из нескольких уроков. Всего есть 3 вида уроков:
* `free` - бесплатный урок, доступен всем
* `demo` - авторизованные пользователи могут запросить демо версию урока
* `vip` - доступен пользователям с ролью `vip` 

Авторизация в сервисе основана на JWT со следующей структурой:
```
{
    "sub":      p.UserID,          // id пользователя
    "username": p.Username,        // логин
    "role":     p.Role,            // роль
    "jti":      jti,               // уникальный идентификатор токена
    "iat":      time.Now().Unix(),    // время выпуска токена
    "exp":      time.Now().Add(p.TTL).Unix(),    // время жизни токена (24 часа)
    "one_time": true               // опциональное поле для одноразовых токенов
}
```
При регистрации пользователя нам выдается токен с `"role": "user"` и с помощью него мы можем запросить демо версию урока. Но для начала разберемся где находится флаг. Поискав по коду или найдя нужный урок в UI делаем вывод, что нам нужно получить доступ к VIP уроку с `id: 16` из курса с `id: 4`. Контент для VIP уроков обернут в `middleware` с проверкой роли и требует указания некого `slug` в качестве path параметра:
```
vipContent.Use(authMw, middleware.RequireRole("vip"))
{
    vipContent.GET("/courses/:course_id/lessons/access/:slug", lessonHandler.GetVipLesson)
}
```
`slug` - это еще один токен, который генерируется на основе SHA256 от конкатенации `id` запрашиваемого урока и `jti` токена пользователя, который инициировал запрос:
```
func Generate(lessonID int, jti string, secret string) string {
    data := fmt.Sprintf("%d:%s", lessonID, jti)

    mac := hmac.New(sha256.New, []byte(secret))
    mac.Write([]byte(data))
    signature := mac.Sum(nil)

    raw := fmt.Sprintf("%d:%x", lessonID, signature)
    return base64.RawURLEncoding.EncodeToString([]byte(raw))
}
```
При этом `id` курса не участвует в генерации `slug` токена, и кажется, что можно попробовать поискать другой урок с таким же `id`, но другого урока с `id: 16` нет. Поэтому обойти проверку `slug` не получится. Но для начала нам стоит разбораться с тем, как пройти проверку на наличие роли `vip`.
Обычный пользователь может запрашивать демо доступ для уроков с типом `demo`. Доступ к такому уроку предоставляется особенным образом - нам выдают два токена:
```
{
    "token": tokenString,      // JWT, генерируемый тем же способом. что и наш авторизационный токен
    "slug":  lessonSlug        // токен, описанный выше
}
```
JWT для демо урока, внезапно, дает нам временную роль `vip` - на один запрос или на 10 секунд:
```
tokenString, jti, err := h.auth.IssueToken(auth.TokenParams{
    UserID:   claims.Sub,           // токен выписывается на наш id
    Username: claims.Username,      // и наш логин
    Role:     "vip",                // но с ролью "vip"
    OneTime:  true,
    TTL:      10 * time.Second,
})
```
По истечении 10 секунд или при отправке запроса с этим токеном - он отзывается. Токен похож на наш токен авторизации и подписывается на основе того же секрета - отсюда очевидный вектор использовать полученный токен для обхода проверки `middleware`. Поискав, что еще можно сделать с ролью VIP пользователя можно найти следующий код:
```
type lessonListItem struct {
    ID    int    `json:"id"`
    Title string `json:"title"`
    Type  string `json:"type"`
    Slug  string `json:"slug,omitempty"`
}

func (h *CourseHandler) GetCourse(c *gin.Context) {
    courseID, err := strconv.Atoi(c.Param("course_id"))
    ...

    claims, _ := middleware.GetClaims(c)
    isVIP := claims != nil && claims.Role == "vip"

    lessons := make([]lessonListItem, len(course.Lessons))
    for i, l := range course.Lessons {
        item := lessonListItem{
            ID:    l.ID,
            Title: l.Title,
            Type:  l.Type,
        }
        if isVIP && (l.Type == "vip" || l.Type == "demo") {
            item.Slug = slug.Generate(l.ID, claims.JTI, h.slugSecret)    // если роль "vip", то в списке уроков для курса будут присутствовать slug токены от VIP уроков
        }
        lessons[i] = item
    }

    c.JSON(http.StatusOK, gin.H{
        "id":          course.ID,
        "title":       course.Title,
        "description": course.Description,
        "lessons":     lessons,
    })
}
```
VIP пользователи получают `slug` токены для VIP уроков по запросу `/api/courses/:course_id`. Таким образом для получения флага нам нужно сделать 2 запроса: получить `slug` токены для уроков из курса с `id: 4` и получить контент от урока с `id: 16`. Но так как токен с ролью `vip` одноразовый, нужно разобраться с функционалом отзыва токенов.

Для отзыва используется отдельный сервис `revocation`. Сервис имеет два основных эндпоинта:
* `/check` - проверяет отозван ли токен
* `/revoke` - отзывает токен
 Для хранения отозыванных токенов используется файл:
 ```
 func main() {
    logger, _ := zap.NewProduction()
    defer logger.Sync()

    dataFile := envOrDefault("DATA_FILE", "/data/revoked.txt")
    port := envOrDefault("PORT", "8081")

    store := internal.NewStore(dataFile, logger)
    service := internal.NewService(store, logger)

    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    service.StartCleanupTask(ctx)

    ...
}
```
Рассмотрим код проверки отзыва:
```
func (s *Service) CheckRevoked(jti string) (bool, error) {
    ch := make(chan bool)

    go func() {
        s.store.mu.Lock()
        defer s.store.mu.Unlock()
        revoked := s.store.IsRevoked(jti)
        ch <- revoked
    }()

    select {
    case result := <-ch:
        return result, nil
    case <-time.After(50 * time.Millisecond):
        return false, fmt.Errorf("check timeout")
    }
}
```
Когда сервис получает токен для проверки запускается горутина, которая захватывает мьютекс, читает файл и отправляет результат в канал `ch`. Основной поток при этом ожидает результат с таймаутом 50 мс. При этом канал `ch` небуферизированный, что дает возможность реализовать дедлок: если файл с отозыванными токенами будет достаточно большой, то функция `IsRevoked` может выполниться медленнее чем 50 мс. Тогда сработает таймаут, и основной поток завершится, не прочитав результат из канала. Горутина будет пытаться отправить `revoked` в `ch`, но получатель больше не читает канал, `defer s.store.mu.Unlock()` не выполнится и все это приводит к `panic` и ошибке работы сервиса `revocation`. А при ошибке проверки токена сервис не отправляет информацию об отзыве токена и значит основной сервис будет считать, что токен действителен.
```
func (h *Handler) Check(c *gin.Context) {
    var req struct {
        JTI string `json:"jti" binding:"required"`
    }
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Поле jti обязательно"})
        return
    }

    revoked, err := h.service.CheckRevoked(req.JTI)
    if err != nil {
        h.logger.Error("ошибка проверки отзыва", zap.Error(err))
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Внутренняя ошибка"})
        return       // сервис возвращает ошибку, не сообщая о том, что токен нельзя использовать
    }

    c.JSON(http.StatusOK, gin.H{"revoked": revoked})
}
```
Таким образом план атаки следующий:
1. Регисттрируем пользователя
2. Нагружаем сервис отзыва токенов, запрашивая доступ к демо урокам параллельными запросами
3. Добиваемся дедлока на файле с отозванными токенами
4. Пытаемся получить `slug` токен для необходимого урока и запрашиваем его контент

Пример кода с реализацией атаки: [solve.py](https://github.com/andreika47/Quiet-CTF/blob/main/basecamp/solve.py)

#web #go #jwt #race_condition