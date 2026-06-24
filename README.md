# Kitchen VK Bot

Backend ВК-бота для кухни кафе: официант отправляет заказ текстом, повар отмечает готовность блюд кнопками, админ управляет сотрудниками и выгружает историю в Excel.

## Что уже есть

- FastAPI endpoint `POST /vk/callback` для VK Callback API.
- Подтверждение сервера VK через событие `confirmation`.
- Роли `admin`, `waiter`, `cook` и мягкое удаление сотрудников.
- Первый администратор через `SUPERADMIN_VK_ID` при `/start`.
- Парсинг заказа из обычного текста.
- Подтверждение заказа или автоотправка на кухню через `AUTO_SEND_ORDERS`.
- Callback-кнопки готовности блюд.
- Защита действий по ролям.
- Идемпотентность входящих VK-событий через `vk_event_id`.
- PostgreSQL-модели и Alembic-миграция.
- Команды `/orders`, `/done`, `/users`, `/export`, `/stats`, `/stops`.
- Стоп-лист с хранением 12 часов.
- Excel-экспорт `.xlsx` с листами `Orders`, `Items`, `Events`, `Users`, `Stats`.

## Запланировано

- Раздел `Задачи кафе`: администраторы создают задачи свободным текстом, сотрудники видят активные задачи кнопками и отмечают результат `выполнено` или `запороли/отменили`.

Подробности по этому разделу лежат в [docs/cafe_tasks.md](docs/cafe_tasks.md).

## Команды бота

`/start` — подключиться к боту.

`/myid` — узнать свой VK ID.

`/menu` — меню по роли.

`/help` — подсказка по формату заказа и стопам.

`/add <vk_id> <role> <name>` — добавить сотрудника, только admin.

`/remove <vk_id>` — деактивировать сотрудника, только admin.

`/users` — список сотрудников, только admin.

`/orders` — активные заказы.

`/done` — выполненные заказы.

`/export today` — Excel за сегодня, только admin.

`/export 2026-06-01 2026-06-24` — Excel за период, только admin.

`/stats today` — базовая статистика, только admin.

`/stops` — актуальные стопы.

Кнопка `Стопы` — открыть стоп-лист и включить режим добавления стопов. После этого обычный текст становится новым стопом.

`/stop нет борща до 18:00` или `/stops нет борща до 18:00` — добавить сообщение в стоп-лист.

Чтобы выйти из режима стопов, нажмите `Меню` или `Активные`.

Обычный текст от `waiter` или `admin`, похожий на заказ, создаёт заказ:

```text
Стол 4
борщ 2
паста 1
лимонад 1
комм: пасту без лука
```

Сырой текст заказа видит автор и администраторы. Повара получают только распарсенный кухонный формат с позициями и кнопками.

## Локальный запуск

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
pytest
```

Если зависимости ещё не установлены, можно проверить чистую бизнес-логику:

```bash
python scripts/smoke_check.py
```

## Railway

1. Создайте GitHub-репозиторий и отправьте туда этот проект.
2. В Railway создайте новый проект из GitHub repo.
3. Добавьте PostgreSQL service.
4. В переменных Railway заполните значения из `.env.example`.
5. Укажите `PUBLIC_BASE_URL` как публичный домен Railway, например `https://your-app.up.railway.app`.
6. Start command уже задан в `railway.json`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Перед первым рабочим запуском выполните миграции:

```bash
alembic upgrade head
```

В Railway это можно сделать через shell/one-off command. После миграции сервис готов принимать VK Callback.

## VK

В настройках сообщества:

1. Включите сообщения сообщества.
2. Включите Bot settings и Callback API.
3. URL сервера: `https://<railway-domain>/vk/callback`.
4. Secret должен совпадать с `VK_SECRET`.
5. Confirmation code должен совпадать с `VK_CONFIRMATION_CODE`.
6. Включите события `message_new` и `message_event`.

После подтверждения сервера напишите `/start` от VK ID, указанного в `SUPERADMIN_VK_ID`.

## Переменные окружения

`DATABASE_URL` — PostgreSQL URL Railway. Поддерживаются `postgres://`, `postgresql://` и `postgresql+asyncpg://`.

`VK_TOKEN` — токен сообщества VK.

`VK_GROUP_ID` — ID сообщества.

`VK_SECRET` — secret для Callback API.

`VK_CONFIRMATION_CODE` — код подтверждения сервера.

`SUPERADMIN_VK_ID` — VK ID первого администратора.

`APP_TIMEZONE` — часовой пояс отчётов.

`AUTO_SEND_ORDERS` — `true`, если заказ надо сразу слать на кухню без подтверждения.

`TOGGLE_ITEM_READY` — `true`, если повторное нажатие снимает готовность.

`KITCHEN_MODE` — `private` или `peer_chat`.

`KITCHEN_PEER_ID` — ID кухонной беседы, если выбран `peer_chat`.

`STOPS_TTL_HOURS` — срок актуальности сообщений стоп-листа.

`PUBLIC_BASE_URL` — публичный URL Railway для ссылок на Excel.

## Важные замечания

- Бот не пишет сотруднику первым, если пользователь ещё не разрешил сообщения от сообщества. Сотруднику нужно открыть сообщения сообщества и написать `/start`.
- В MVP кухня по умолчанию получает заказы личными сообщениями всем активным `cook` и `admin`.
- Excel сейчас отдаётся ссылкой `/exports/<file>.xlsx`. Для боевого кафе лучше держать `PUBLIC_BASE_URL` заполненным.
- История сохраняется даже после деактивации сотрудника.
