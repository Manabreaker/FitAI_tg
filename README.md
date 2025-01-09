# FitAI: Ваш персональный AI-фитнес-тренер

FitAI - это проект, предназначенный для создания персонализированных планов тренировок и питания с помощью искусственного интеллекта. Пользователь предоставляет свои данные (возраст, пол, вес, рост, цель, уровень подготовки), а бот генерирует индивидуальные рекомендации, соответствующие их потребностям.

## Основной функционал
- **Создание персональных рационов питания** с учетом цели пользователя (похудение, набор массы, поддержание формы).
- **Составление программ тренировок**, адаптированных под уровень подготовки и физические параметры пользователя.
- **Хранение истории общения**: все сообщения пользователя и ответы бота записываются в файл, уникальный для каждого пользователя, по их Telegram ID.

## Установка

### Шаг 1: Клонирование репозитория
```bash
git clone <https://github.com/Manabreaker/FitAI_tg>
cd FitAI
```

### Шаг 2: Установка зависимостей
Используйте `pip` для установки необходимых библиотек:
```bash
pip install -r requirements.txt
```

### Шаг 3: Конфигурация
Создайте файл `config.py` и добавьте следующие настройки:
```python
# Имя модели для общения с AI
g4f_model_name = "your_model_name_here"

# Включение режима тестирования
TestMode = True  # Установите False для отключения логирования
```

## Использование

### 1. Запуск проекта
Запустите скрипт:
```bash
python main.py
```

### 2. Взаимодействие с ботом
После запуска бот готов принимать команды от пользователей в Telegram. Первичная регистрация включает сбор данных о пользователе, таких как:
- Имя
- Возраст
- Пол
- Вес
- Рост
- Цель тренировок
- Уровень подготовки

После регистрации пользователи могут отправлять команды для получения планов питания или тренировок.

## Архитектура
- **`FitAI`**: Класс, отвечающий за взаимодействие с моделью ИИ и обработку пользовательских данных.
- **Запись данных**: Все сообщения сохраняются в папке `user_data`, где каждый пользователь идентифицируется по своему Telegram ID.
- **Обработка состояний**: Используется FSM для управления процессом регистрации.

## Основные файлы
- `main.py` - Главный файл для запуска бота.
- `fit_ai.py` - Основная логика взаимодействия с AI.
- `config.py` - Конфигурационный файл.
- `requirements.txt` - Зависимости проекта.
- `user_data/` - Папка для хранения истории взаимодействия с пользователями.

## Пример работы
1. **Регистрация пользователя:**
   Пользователь предоставляет свои данные через последовательность вопросов.
2. **Запрос программы тренировок:**
   Пользователь отправляет запрос "Составь программу тренировок".
3. **Результат:**
   Бот возвращает структурированный план тренировок, соответствующий параметрам пользователя.

## Требования
- Python 3.9+
- Установленные зависимости из `requirements.txt`

## Дополнительные возможности
- Логирование ошибок и сообщений для удобного тестирования и отладки.
- Поддержка русскоязычного интерфейса.

## Планируемые улучшения
- Добавление интеграции с устройствами для трекинга (например, шагомеры, пульсометры).
- Визуализация данных о прогрессе пользователя.
- Расширение возможностей взаимодействия с ботом (например, добавление голосовых команд).

## Лицензия
Проект распространяется под лицензией MIT.

## Контакты
Если у вас есть вопросы или предложения, свяжитесь с автором через Telegram или GitHub:
- GitHub: [Manabreaker](https://github.com/Manabreaker)

