# Реализация площадки бартерного обмена предметами между пользователями

Стек: Django 4.2.23, Ddjango Rest Framework 3.16.0, SQLite.

Интерфейсы: веб-интерфейс, JSON API.

Клонировать в среде PYCharm, добавить фиртуальное окружение, скачать пакеты:

cd sharing_platform
pip install -r requirements.txt

 manage.py makemigratons
 
 manage.py migrate
 
 manage.py createsuperuser

  manage.py collectstatic

  manage.py runserver

В админке создадим пару категорий *(Первичный ключ - автоинкремент)*
Создадим второго и третьего пользователя. Также в админке можно создать токена авторизации для других тестовых пользователей.

 JSON API
 ----

Теперь можно авторизироваться через, например, *Postman*, и загрузить сразу несколько фейковых данных, предсатвляющих экземпляры *вещей* для обмена

**Авторизация по API**

Получение токена авторизации через запрос к *api* *rest-framework*, с передачей данных для авторизации

![auth1](https://github.com/filthps/sharing-platform/blob/master/readme/jsonapi1.png?raw=true)
![auth2](https://github.com/filthps/sharing-platform/blob/master/readme/jsonapi2.png?raw=true)


Теперь можно загурзить данные *Приведу простой и рабочий пример данных, который можно загрузить*:


{
    "ads": [
        {
            "name": "Мышь",
            "description": "Беспроводная",
            "category": 1,
            "owner": 1
        },
        {
            "name": "Утюг",
            "category": 2,
            "owner": 1
        },
        {
            "name": "Колесо велосипедное",
            "description": "Есть лопнувшие спицы",
            "status": "b",
            "category": 1,
            "owner": 1
        },
        {
            "name": "Цифро-аналоговый преобразователь TEAC UD-501",
            "description": "Практически не использовался",
            "status": "a",
            "category": 2,
            "owner": 3
        },
        {
            "name": "Резец токарный T15K6 проходной",
            "description": "Без пластины",
            "status": "b",
            "category": 3,
            "owner": 3
        },
        {
            "name": "Фреза концевая диаметр 12",
            "status": "a",
            "category": 3,
            "owner": 3
        }
    ]
}

![data-json](https://github.com/filthps/sharing-platform/blob/master/readme/seccessed-load-json-data.png?raw=true)

----

Теперь, заглянув в *ad/urls.py*, можно найти *url*, которым можно инициировать процесс обмена

![request-send](https://github.com/filthps/sharing-platform/blob/master/readme/send-request.png?raw=true)

Можно убедиться, что заявка появилась.

![request-added](https://github.com/filthps/sharing-platform/blob/master/readme/browser/request.png?raw=true)

Можно убедиться, что при повторых обращениях дубликат заявки не появится.

Попытка откликнутьсся на заявку, будучи посторонним пользовтаелем, не изменит состояние заявки.

![request-error](https://github.com/filthps/sharing-platform/blob/master/readme/bad-request.png?raw=true)

---

Отменим свой запрос.

![request-cancel](https://github.com/filthps/sharing-platform/blob/master/readme/remove-my-request.png?raw=true)

Создадим другой запрос на обмен. 
Возьмём в *Postman* токен авторизации от постороннего пользователя, и попробум поменять состояние заявки на обмен, убедимся, что ничего не вышло :)

![request-error](https://github.com/filthps/sharing-platform/blob/master/readme/error-sender-accept-request.png)

Возьмём в *Postman* токен авторизации от *получаетля заявки* и примем заявку!

![request-error](https://github.com/filthps/sharing-platform/blob/master/readme/accept.png?raw=true)

А теперь попробуем сделать это ещё раз: так как метод *PUT* не идемпотентен - ожидаем кода ошибки.

![request-error](https://github.com/filthps/sharing-platform/blob/master/readme/repeat-accept-error.png?raw=true)

----

И, наконец, убедимся, что заявок нет

![request-list-empty](https://github.com/filthps/sharing-platform/blob/master/readme/browser/no-items.png?raw=true)
