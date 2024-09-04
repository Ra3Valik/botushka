from crud import add_user, update_user_score, add_chat, check_user_exist, check_user_exist_by_user_id
import telebot
from dotenv import load_dotenv
import os
import re

load_dotenv()

bot = telebot.TeleBot(os.getenv("TOKEN"))


# Обработчик всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if "++ @" in message.text:
        # Регулярное выражение для поиска всех вхождений после "++ @"
        mentions = re.findall(r"\+\+ @(\w+)", message.text)
        if mentions:
            for mention in mentions:
                if check_user_exist(chat_id, mention):
                    update_user_score(chat_id, mention)
                    # Отправить сообщение о начисленных баллах
                else:
                    # Отправить сообщение что такого пользователя не найдено
                    continue
    if "-- @" in message.text:
        # Регулярное выражение для поиска всех вхождений после "-- @"
        mentions = re.findall(r"\-\- @(\w+)", message.text)
        if mentions:
            for mention in mentions:
                if check_user_exist(chat_id, mention):
                    update_user_score(chat_id, mention, -1)
                    # Отправить сообщение о списанных баллах
                else:
                    # Отправить сообщение что такого пользователя не найдено
                    continue

    if (check_user_exist_by_user_id(chat_id, user_id)):
        username = message.from_user.username
        if username:
            add_user(user_id, chat_id, username, 0)


@bot.message_handler(content_types=['new_chat_members'])
def on_new_chat_member(message):
    for new_member in message.new_chat_members:
        # Проверяем, что добавлен именно бот
        if new_member.id == bot.get_me().id:
            bot.send_message(message.chat.id, "Спасибо за добавление в группу! Теперь мы будем внимательно следить за вашими Е-баллами <3")
            add_chat(message.chat.id)


bot.infinity_polling()
