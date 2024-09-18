from lib.crud import add_user, update_user_score, add_chat, check_user_exist, check_user_exist_by_user_id, add_message, \
    get_user_id_from_nickname, clear_chat_score, get_chat_ranking, get_user_messages, get_all_user_messages, check_chat_exist
from lib.helpers import env_variables, is_integer
from app.bot_phrases import get_user_not_found_message, get_user_odd_point_message, get_user_add_point_message
import telebot
from telebot.types import BotCommand
import re

bot = telebot.TeleBot(env_variables.get('TOKEN'))

# Определяем команды
commands = [
    BotCommand(command="/help", description="Помощь по командам"),
    BotCommand(command="/clear_score", description="Очистить счёт Е-баллов"),
    BotCommand(command="/top", description="Посмотреть счет пользователя"),
    BotCommand(command="/get_user_score", description="Посмотреть счет пользователя"),
    BotCommand(command="/get_user_score_history", description="Посмотреть историю изменения очков пользователя очков "
                                                              "пользователя"),
]

# Устанавливаем команды в меню бота
bot.set_my_commands(commands)


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "Список команд:\n"
                          "/help - вывести список команд\n"
                          "/clear_score - очищает счёт всех пользователей\n"
                          "/top - Выводит топ 10 пользователей по E-баллам\n"
                          "/get_user_score - посмотреть счёт пользователя и историю его пополнения\n"
                          "/get_user_score_history -  посмотреть счёт пользователя и историю его пополнения в т.ч. "
                          "для уже очищенных очков\n\n\n"
                          "По всем вопросам, багам и предложением: @Ra3Valik")


@bot.message_handler(content_types=['new_chat_members'])
def on_new_chat_member(message):
    for new_member in message.new_chat_members:
        # Проверяем, что добавлен именно бот
        if new_member.id == bot.get_me().id:
            bot.send_message(
                message.chat.id,
                "Спасибо за добавление в группу! Теперь мы будем внимательно следить за вашими Е-баллами <3"
            )
            if (not check_chat_exist(message.chat.id)):
                add_chat(message.chat.id)
        elif (not check_user_exist_by_user_id(message.chat.id, new_member.id)):
            username = new_member.username
            if username:
                add_user(new_member.id, message.chat.id, username, 0)



@bot.message_handler(commands=['clear_score'])
def handle_clear_score(message):
    chat_id = str(message.chat.id)
    result = clear_chat_score(chat_id)
    bot.reply_to(message, result)


@bot.message_handler(commands=['top'])
def handle_get_ranking(message):
    chat_id = str(message.chat.id)
    result = get_chat_ranking(chat_id)
    bot.reply_to(message, result)


@bot.message_handler(commands=['get_user_score'])
def handle_get_user_score(message):
    chat_id = str(message.chat.id)
    # Считываем текст сообщения после команды
    # Формат: /get_user_messages @username
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            mention = parts[1].strip()
            match = re.match(r"@(\w+)", mention)
            if not match:
                username = message.from_user.username
            else:
                username = match.group(1)
        else:
            username = message.from_user.username

        user_id = get_user_id_from_nickname(chat_id, username)
        if user_id:
            result = get_user_messages(chat_id, user_id)
            bot.reply_to(message, result)
        else:
            bot.reply_to(message, get_user_not_found_message(username))
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")


# Команда для вывода всех сообщений пользователя
@bot.message_handler(commands=['get_user_score_history'])
def handle_get_user_score_history(message):
    chat_id = str(message.chat.id)
    # Считываем текст сообщения после команды
    # Формат: /get_all_user_messages @username
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            mention = parts[1].strip()
            match = re.match(r"@(\w+)", mention)
            if not match:
                username = message.from_user.username
            else:
                username = match.group(1)
        else:
            username = message.from_user.username

        user_id = get_user_id_from_nickname(chat_id, username)
        if user_id:
            result = get_all_user_messages(chat_id, user_id)
            bot.reply_to(message, result)
        else:
            bot.reply_to(message, get_user_not_found_message(username))
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")


# Обработчик всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Проверяем автора сообщения на наличие его в базе
    # Внедрить сюда кэш, чтоб не делать постоянно запросы к базе
    if (not check_user_exist_by_user_id(chat_id, user_id)):
        username = message.from_user.username
        if username:
            add_user(user_id, chat_id, username, 0)

    # Проверяем или надо добавлять карму
    # Регулярное выражение для поиска упоминаний и чисел с последующим сообщением
    pattern = r"@(\w+)\s*([+-]\d+)\s*(.*?)(?=@\w+\s*[+-]\d+|$)"

    # Ищем все упоминания, числа и их соответствующие сообщения
    matches = re.findall(pattern, message.text, re.DOTALL)
    if matches:
        for mention, number, user_message in matches:
            if check_user_exist(chat_id, mention):
                if is_integer(number):
                    number = int(number)
                    if number == 0:
                        bot.reply_to(message, 'Плюс минус ноль? Я что в песне Noize MC?')
                        return
                    elif number > 0:
                        bot.reply_to(message, get_user_add_point_message(mention, number))
                    elif number < 0:
                        bot.reply_to(message, get_user_odd_point_message(mention, number))
                    update_user_score(chat_id, mention, number)
                    add_message(chat_id, user_id, user_message, message.from_user.username, number)

            else:
                bot.reply_to(message, get_user_not_found_message(mention))
                continue


bot.infinity_polling()
