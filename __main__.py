import telebot
from lib.crud import add_user, update_user_score, add_chat, check_user_exist_by_telegram_user_id, add_message, \
    get_user_id_from_username, clear_chat_score, get_chat_ranking, get_user_messages, get_all_user_messages, check_chat_exist
from lib.helpers import env_variables, is_integer
from app.bot_phrases import get_user_not_found_message, get_user_odd_point_message, get_user_add_point_message, \
    get_user_hello_message, get_user_no_chats_message, get_allowed_only_in_private_chat_message, \
    get_only_one_point_message
from telebot.types import BotCommand
import re
from lib.keyboard import get_settings_keyboard_markup, bot_keyboard_buttons_handler, maybe_change_points
from lib.state import awaiting_count_of_point
from lib.errors import log_error
from lib.functions import send_response, handle_points_update, sort_users, can_modify_points, get_remaining_message, \
    extract_mentions_and_number, send_self_mention_message, extract_points_and_text, send_long_message

bot = telebot.TeleBot(env_variables.get('TOKEN'))

# Определяем команды
commands = [
    BotCommand(command="/help", description="Помощь по командам"),
    BotCommand(command="/clear_score", description="Сбросить счёт Е-баллов"),
    BotCommand(command="/top", description="Топ пользователей по счёту"),
    BotCommand(command="/get_user_score", description="Счёт пользователя"),
    BotCommand(command='/settings', description="Настроить группы (только в лс)")
]

# Устанавливаем команды в меню бота
bot.set_my_commands(commands)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    bot_keyboard_buttons_handler(call, bot)


@bot.message_handler(content_types=['new_chat_members'])
def on_new_chat_member(message):
    for new_member in message.new_chat_members:
        # Проверяем, что добавлен именно бот
        if new_member.id == bot.get_me().id:
            message_text = get_user_hello_message()
            bot.send_message(
                message.chat.id,
                message_text
            )
            if (not check_chat_exist(message.chat.id)):
                add_chat(message.chat.id, message.chat.title)
        elif (not check_user_exist_by_telegram_user_id(message.chat.id, new_member.id)):
            username = new_member.username
            if username:
                add_user(new_member.id, message.chat.id, username, 0)


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "Список команд:\n"
                          "/help - вывести список команд\n"
                          "/clear_score - очищает счёт всех пользователей\n"
                          "/top - выводит топ 10 пользователей по E-баллам\n"
                          "/get_user_score - посмотреть счёт пользователя и историю его пополнения\n"
                          "/settings - Настройки бота и отправка кармы, работает только в личных сообщениях\n\n\n"
                          "По всем вопросам, багам и предложением: @Ra3Valik")


@bot.message_handler(commands=['settings'])
def start_message(message):
    chat_type = message.chat.type

    if chat_type == 'private':
        markup = get_settings_keyboard_markup()
        if markup:
            bot.send_message(message.chat.id, "Выберите кнопку:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, get_user_no_chats_message())
    else:
        bot.send_message(message.chat.id, get_allowed_only_in_private_chat_message())


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

        user_id = get_user_id_from_username(chat_id, username)
        if user_id:
            result = get_user_messages(chat_id, user_id)
            send_long_message(bot, message, result)
        else:
            bot.reply_to(message, get_user_not_found_message(username))
    except Exception as e:
        log_error(f"handle_get_user_score {str(e)}")


# Команда для вывода всех сообщений пользователя
# @bot.message_handler(commands=['get_user_score_history'])
# def handle_get_user_score_history(message):
#     chat_id = str(message.chat.id)
#     # Считываем текст сообщения после команды
#     # Формат: /get_all_user_messages @username
#     try:
#         parts = message.text.split(maxsplit=1)
#         if len(parts) > 1:
#             mention = parts[1].strip()
#             match = re.match(r"@(\w+)", mention)
#             if not match:
#                 username = message.from_user.username
#             else:
#                 username = match.group(1)
#         else:
#             username = message.from_user.username
#
#         user_id = get_user_id_from_username(chat_id, username)
#         if user_id:
#             result = get_all_user_messages(chat_id, user_id)
#             send_long_message(bot, message, result)
#         else:
#             bot.reply_to(message, get_user_not_found_message(username))
#     except Exception as e:
#         log_error(f"handle_get_user_score_history {str(e)}")


# Обработчик всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    telegram_user_id = message.from_user.id
    chat_type = message.chat.type

    # Если это личные сообщения и мы ожидаем кол-во для изменения баллов
    if chat_type == 'private':
        if awaiting_count_of_point.get(telegram_user_id):
            user_id = awaiting_count_of_point.get(telegram_user_id)
            del awaiting_count_of_point[telegram_user_id]
            maybe_change_points(message, user_id, bot)
        return

    # Проверяем автора сообщения на наличие его в базе
    if not check_user_exist_by_telegram_user_id(chat_id, telegram_user_id):
        username = message.from_user.username
        if username and message.from_user.is_bot == False:
            add_user(telegram_user_id, chat_id, username, 0)

    # ДРУГАЯ ОБРАБОТКА
    # Если сообщение содержит собаку, то скорее всего кто-то пытается баллы изменить
    if '@' in message.text:
        # Извлечение упоминаний и числа из сообщения
        mentions, number = extract_mentions_and_number(message.text)

        # Проверка, что количество баллов не равно 0
        if number == 0 or not is_integer(number):
            return

        # Проверка прав пользователя на изменение больше чем на 1 балл
        if not can_modify_points(chat_id, telegram_user_id, number, bot):
            bot.reply_to(message, get_only_one_point_message())
            return

        # Получение оставшегося текста после удаления упоминаний и числа
        remaining_message = get_remaining_message(message.text, number, mentions)

        # Разделение пользователей на существующих, несуществующих и самозванцев
        founded_user, not_founded_user, self_mention = sort_users(chat_id, mentions, message.from_user.username)

        # Обработка самозванцев, если таковые есть
        send_self_mention_message(bot, message, self_mention)

        # Обновление баллов для существующих пользователей
        handle_points_update(chat_id, founded_user, number, remaining_message, telegram_user_id,
                             message.from_user.username)

        # Отправка ответов с результатами
        send_response(bot, message, founded_user, not_founded_user, number)
        return # Прерываем дальнейшую обработку, так как это сообщение уже обработано

    # ДРУГАЯ ОБРАБОТКА
    # Если сообщение является ответом на другое сообщение
    if message.reply_to_message and message.reply_to_message.from_user.is_bot == False:
        # Извлечение значения баллов из первого слова сообщения
        reply_points, reply_message_text = extract_points_and_text(message.text)

        if reply_points == 0 or not is_integer(reply_points):
            return

        if reply_points:
            # Получаем ID пользователя, на чьё сообщение ответили
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username

            # Проверка на самозванца
            if target_user_id == telegram_user_id:
                send_self_mention_message(bot, message, target_username)
                return

            # Проверка прав пользователя на изменение больше чем на 1 балл
            if not can_modify_points(chat_id, telegram_user_id, reply_points, bot):
                bot.reply_to(message, get_only_one_point_message())
                return

            # Обновление баллов и добавление сообщения в историю
            update_user_score(chat_id, target_username, reply_points)
            add_message(chat_id, target_user_id, reply_message_text, message.from_user.username, reply_points)

            # Отправка соответствующего сообщения
            if reply_points > 0:
                bot.reply_to(message, get_user_add_point_message([target_username], reply_points))
            elif reply_points < 0:
                bot.reply_to(message, get_user_odd_point_message([target_username], reply_points))

            return


bot.infinity_polling()
