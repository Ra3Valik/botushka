from lib.crud import add_user, update_user_score, add_chat, check_user_exist, check_user_exist_by_telegram_user_id, add_message, \
    get_user_id_from_nickname, clear_chat_score, get_chat_ranking, get_user_messages, get_all_user_messages, check_chat_exist
from lib.helpers import env_variables, is_integer
from app.bot_phrases import get_user_not_found_message, get_user_odd_point_message, get_user_add_point_message, get_user_hello_message, get_user_no_chats_message, get_allowed_only_in_private_chat_message
import telebot
from telebot.types import BotCommand
import re
from lib.keyboard import get_chats_keyboard_markup, get_start_keyboard_markup, bot_keyboard_buttons_handler, maybe_change_points
from lib.state import awaiting_count_of_point

bot = telebot.TeleBot(env_variables.get('TOKEN'))

# Определяем команды
commands = [
    BotCommand(command="/help", description="Помощь по командам"),
    BotCommand(command="/clear_score", description="Очистить счёт Е-баллов"),
    BotCommand(command="/top", description="Посмотреть счет пользователя"),
    BotCommand(command="/get_user_score", description="Посмотреть счет пользователя"),
    BotCommand(command="/get_user_score_history", description="Посмотреть историю изменения очков пользователя очков "
                                                              "пользователя"),
    BotCommand(command='/settings', description="Установить тех кто может управлять чатом (работает "
                                                            "только в личных сообщениях с ботом)")
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
                add_chat(message.chat.id)
        elif (not check_user_exist_by_telegram_user_id(message.chat.id, new_member.id)):
            username = new_member.username
            if username:
                add_user(new_member.id, message.chat.id, username, 0)


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "Список команд:\n"
                          "/help - вывести список команд\n"
                          "/clear_score - очищает счёт всех пользователей\n"
                          "/top - Выводит топ 10 пользователей по E-баллам\n"
                          "/get_user_score - посмотреть счёт пользователя и историю его пополнения\n"
                          "/get_user_score_history -  посмотреть счёт пользователя и историю его пополнения в т.ч. "
                          "для уже очищенных очков\n\n"
                          "/settings - Настройки бота и отправка кармы в личных сообщениях\n\n\n"
                          "По всем вопросам, багам и предложением: @Ra3Valik")


@bot.message_handler(commands=['settings'])
def start_message(message):
    chat_type = message.chat.type

    if chat_type == 'private':
        markup = get_start_keyboard_markup()
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
    telegram_user_id = message.from_user.id
    chat_type = message.chat.type

    # Если это личные сообщения и мы ожидаем кол-во для изменения баллов
    if chat_type == 'private':
        if awaiting_count_of_point[telegram_user_id]:
            maybe_change_points(message, awaiting_count_of_point[telegram_user_id], bot)
            del awaiting_count_of_point[telegram_user_id]
        return

    # Проверяем автора сообщения на наличие его в базе
    if (not check_user_exist_by_telegram_user_id(chat_id, telegram_user_id)):
        username = message.from_user.username
        if username:
            add_user(telegram_user_id, chat_id, username, 0)

    # Если сообщение содержит собаку, то скорее всего кто-то пытается баллы изменить
    if '@' in message.text:
        # Регулярное выражение для нахождения упоминаний, числа (или символов ++, --, —) и текста
        pattern = r"(?:@(\w+))|([+-]?\d+|--|\+\+|—)"
        matches = re.findall(pattern, message.text)

        # Извлекаем упоминания
        mentions = [m[0] for m in matches if m[0]]  # Упоминания
        number = None
        remaining_message = None

        # Поиск числа (или символов ++, --, —)
        for m in matches:
            if m[1]:
                if m[1] == '++':
                    number = 1
                elif m[1] == '--' or m[1] == '—':
                    number = -1
                else:
                    number = int(m[1])  # Если это обычное число

        # Очистим сообщение от всех упоминаний
        message_text = message.text
        for mention in mentions:
            message_text = message_text.replace(f"@{mention}", "").strip()

        # Оставшаяся часть сообщения (всё, что после числа) запишем в сообщение об измении баллов
        remaining_message_match = re.search(r"([+-]?\d+|--|\+\+|—) (.+)", message_text)
        if remaining_message_match:
            remaining_message = remaining_message_match.group(2)

        if number or number == 0:
            return

        not_founded_user = []
        founded_user = []
        for mention in mentions:
            if check_user_exist(chat_id, mention):
                update_user_score(chat_id, mention, number)
                add_message(chat_id, telegram_user_id, remaining_message, message.from_user.username, number)
                founded_user.append(mention)
            else:
                not_founded_user.append(mention)
                continue

        if not_founded_user:
            # НАДО ОТПРАВИТЬ СООБЩЕНИЕ ЧТО НЕ НАШЁЛ ЭТИХ ПОЛЬЗОВАТЕЛЕЙ
            bot.reply_to(message, get_user_add_point_message('mention', number))
        if founded_user:
            if number > 0:
                # ПРЕДУСМОТРЕТЬ ЧТО МЕНТНТИОНС МОЖЕТ БЫТЬ МНОГО
                bot.reply_to(message, get_user_add_point_message(mentions, number))
            elif number < 0:
                # ПРЕДУСМОТРЕТЬ ЧТО МЕНТНТИОНС МОЖЕТ БЫТЬ МНОГО
                bot.reply_to(message, get_user_odd_point_message(mentions, number))


bot.infinity_polling()
