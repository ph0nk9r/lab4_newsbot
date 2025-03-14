import os
import logging
import requests
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"


bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)


user_preferences = {}


menu_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
menu_keyboard.add(KeyboardButton("📰 Актуальные новости"))
menu_keyboard.add(KeyboardButton("🔎 Поиск по теме"))
menu_keyboard.add(KeyboardButton("📂 Отобразить последний запрос"))
menu_keyboard.add(KeyboardButton("⚙ Настройки"))


settings_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
settings_keyboard.add(KeyboardButton("📜 Текущая история запросов"))
settings_keyboard.add(KeyboardButton("🗑 Очистить историю запросов"))
settings_keyboard.add(KeyboardButton("⬅ Назад"))


# получить последние новости
def fetch_news(category=None, query=None):
    url = NEWS_API_URL if not query else "https://newsapi.org/v2/everything"  # Базовые параметры запроса
    params = {
        "apiKey": NEWS_API_KEY, 
        "language": "en"
        }  # Базовые параметры запроса

    if category:
        params["category"] = category  # Добавляем категорию, если указана
    if query: 
        params["q"] = query  # Добавляем ключевое слово для поиска, если указано

    try:
        response = requests.get(url, params=params)  # Отправляем запрос
        response.raise_for_status()  # Проверяем наличие ошибки HTTP
        data = response.json()  # Преобразуем ответ в JSON

        if data.get("status") != "ok":  # Проверяем статус API-ответа
            logging.error(f"API Error: {data.get('message', 'Unknown error')}")
            return []
        
        return data.get("articles", [])[:5]  # Берём первые 5 новостей
    
    except requests.exceptions.RequestException as e:
        logging.error(f"API Request Error: {e}")  # Логируем ошибку
        return []  # Возвращаем пустой список, если произошла ошибка


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я новостной бот. Выберите действие:", reply_markup=menu_keyboard)


@bot.message_handler(func=lambda message: message.text == "⚙ Настройки")
def settings(message):
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=settings_keyboard)


@bot.message_handler(func=lambda message: message.text == "📜 Текущая история запросов")
def current_settings(message):
    saved_queries = user_preferences.get(message.chat.id, [])
    if not saved_queries:
        bot.send_message(message.chat.id, "Сохраненные запросы отсутствуют.")
    else:
        bot.send_message(message.chat.id, "Ваши сохраненные запросы:\n" + "\n".join(saved_queries))


@bot.message_handler(func=lambda message: message.text == "🗑 Очистить историю новостей")
def clear_saved_queries(message):
    user_preferences[message.chat.id] = []
    bot.send_message(message.chat.id, "История очищена.")


@bot.message_handler(func=lambda message: message.text == "📂 Отобразить последний запрос")
def show_saved_news(message):
    saved_queries = user_preferences.get(message.chat.id, [])
    if not saved_queries:
        bot.send_message(message.chat.id, "Вы еще не сохранили запросы.")
        return
    latest_query = saved_queries[-1]  # Используем последний сохраненный запрос
    news = fetch_news(query=latest_query)
    if not news:
        bot.send_message(message.chat.id, "Новости по сохраненному запросу не найдены.")
        return
    for article in news:
        text = f"<b>{article['title']}</b>\n{article['description']}\n<a href='{article['url']}'>Читать</a>"
        bot.send_message(message.chat.id, text, parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text == "⬅ Назад")
def back_to_menu(message):
    bot.send_message(message.chat.id, "Возвращаюсь в главное меню.", reply_markup=menu_keyboard)


@bot.message_handler(func=lambda message: message.text == "📰 Актуальные новости")
def latest_news(message):
    news = fetch_news()  # Запрашиваем новости
    if not news:
        bot.send_message(message.chat.id, "Не удалось загрузить новости. Попробуйте позже.")  # Сообщаем, если новостей нет
        return
    for article in news:
        text = f"<b>{article['title']}</b>\n{article['description']}\n<a href='{article['url']}'>Читать</a>"
        bot.send_message(message.chat.id, text, parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text == "🔎 Поиск по теме")
def ask_for_topic(message):
    bot.send_message(message.chat.id, "Введите ключевое слово для поиска новостей.")  # Отправляем новости пользователю


@bot.message_handler(func=lambda message: True)
def search_news(message):
    if message.chat.id not in user_preferences:
        user_preferences[message.chat.id] = []
    user_preferences[message.chat.id].append(message.text)
    if len(user_preferences[message.chat.id]) > 50:
        user_preferences[message.chat.id].pop(0)  # Удаляем старые запросы, если больше 50
    
    news = fetch_news(query=message.text)
    if not news:
        bot.send_message(message.chat.id, "Новости по данной теме не найдены.")  # Если новостей нет, отправляем сообщение
        return
    for article in news:
        text = f"<b>{article['title']}</b>\n{article['description']}\n<a href='{article['url']}'>Читать</a>"
        bot.send_message(message.chat.id, text, parse_mode="HTML")


if __name__ == "__main__":
    bot.polling(none_stop=True)  # Запускаем бота в режиме непрерывного прослушивания сообщений
