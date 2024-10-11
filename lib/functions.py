import re
from lib.crud import can_add_multiple_points, check_user_exist, update_user_score, add_message, get_telegram_user_id_from_username
from app.bot_phrases import get_user_not_found_message, get_user_odd_point_message, get_user_add_point_message, \
    get_self_mentions_message


def extract_points_and_text(message_text):
    """
    Извлекает количество баллов и текст из сообщения.
    Поддерживаемые форматы: ++, --, —, +1, -1, +2, -2 и т.д.
    :param message_text: Текст сообщения
    :return: Кортеж (количество баллов, текст сообщения)
    """
    pattern = r"([+-]?\d+|--|\+\+|—)\s*(.*)"
    match = re.match(pattern, message_text.strip())

    if match:
        # Определение количества баллов
        number_str = match.group(1)
        if number_str == '++':
            number = 1
        elif number_str in ['--', '—']:
            number = -1
        else:
            number = int(number_str)

        # Текст после символа баллов
        text = match.group(2).strip()
        return number, text if text else None
    return None, None


def extract_mentions_and_number(message_text):
    """
    Извлекает упоминания и числовое значение из сообщения.

    :param message_text: Текст сообщения
    :return: Список упоминаний, значение баллов (или ++/--/—)
    """
    pattern = r"@(\w+)\s*(\+\+|--|—|[+-]\d+)?"
    matches = re.findall(pattern, message_text)
    mentions = [m[0] for m in matches if m[0]]  # Список упоминаний
    number = None

    for m in matches:
        if m[1]:  # Если найдено число или символ
            if m[1] == '++':
                number = 1
            elif m[1] == '--' or m[1] == '—':
                number = -1
            else:
                number = int(m[1])  # Если это обычное число
            break  # Найдено первое число/символ, прерываем цикл

    return mentions, number


def get_remaining_message(message_text, number, mentions):
    """
    Возвращает оставшуюся часть сообщения после числа или символов.

    :param message_text: Текст сообщения
    :param number: Число или символы (++/--/—)
    :param mentions: Список упоминаний
    :return: Оставшаяся часть сообщения
    """
    # Очистим сообщение от всех упоминаний
    for mention in mentions:
        message_text = message_text.replace(f"@{mention}", "").strip()

    # Найдем оставшуюся часть сообщения после числа
    if number is not None:
        remaining_message_match = re.search(r"([+-]?\d+|--|\+\+|—) (.+)", message_text)
        if remaining_message_match:
            return remaining_message_match.group(2)
    return None


def can_modify_points(chat_id, telegram_user_id, number, bot):
    """
    Проверяет, может ли пользователь изменять количество баллов больше чем на 1.

    :param chat_id: ID чата
    :param telegram_user_id: ID пользователя
    :param number: Количество баллов
    :param bot: Бот для отправки сообщений
    :return: True, если пользователь может изменить больше 1 балла, иначе False
    """
    return not (number > 1 or number < -1) or can_add_multiple_points(chat_id, telegram_user_id, bot)


def sort_users(chat_id, mentions, from_username):
    """
    Разделяет упомянутых пользователей на существующих и несуществующих,
    а также фиксирует попытки пользователя изменить свои собственные баллы.

    :param chat_id: ID чата
    :param mentions: Список упоминаний
    :param from_username: Имя отправителя сообщения
    :return: Кортеж из трех списков (существующие пользователи, несуществующие пользователи, самозванец)
    """
    not_founded_user = set()
    founded_user = set()
    self_mention = None  # Пользователи, которые пытались изменить свои баллы

    for mention in mentions:
        if mention == from_username:  # Если пользователь пытается изменить свои баллы
            self_mention = mention
        elif check_user_exist(chat_id, mention):
            founded_user.add(mention)
        else:
            not_founded_user.add(mention)

    return list(founded_user), list(not_founded_user), self_mention


def handle_points_update(chat_id, founded_user, number, remaining_message, telegram_user_id, from_username):
    """
    Обновляет баллы для существующих пользователей.

    :param chat_id: ID чата
    :param founded_user: Список существующих пользователей
    :param number: Количество баллов
    :param remaining_message: Оставшаяся часть сообщения
    :param telegram_user_id: ID отправителя
    :param from_username: Имя отправителя
    """
    for mention in founded_user:
        update_user_score(chat_id, mention, number)
        mention_telegram_user_id = get_telegram_user_id_from_username(chat_id, mention)
        add_message(chat_id, mention_telegram_user_id, remaining_message, from_username, number)


def send_response(bot, message, founded_user, not_founded_user, number):
    """
    Отправляет сообщения с результатами изменения баллов.

    :param bot: Экземпляр бота
    :param message: Сообщение, на которое нужно ответить
    :param founded_user: Список пользователей, для которых были изменены баллы
    :param not_founded_user: Список несуществующих пользователей
    :param number: Количество баллов
    """
    if not_founded_user:
        bot.reply_to(message, get_user_not_found_message(not_founded_user))
    if founded_user:
        if number > 0:
            bot.reply_to(message, get_user_add_point_message(founded_user, number))
        elif number < 0:
            bot.reply_to(message, get_user_odd_point_message(founded_user, number))


def send_self_mention_message(bot, message, self_mention):
    """
    Отправляет сообщение о том, что пользователь пытался изменить баллы самому себе.

    :param bot: Экземпляр бота
    :param message: Сообщение, на которое нужно ответить
    :param self_mention: Список пользователей, которые упомянули себя
    """
    if self_mention:
        message_text = get_self_mentions_message(self_mention)
        bot.reply_to(message, message_text)


def send_long_message(bot, message, text, max_length=4096 - 10):
    """
    Разбивает длинное сообщение на части и отправляет по частям, если оно превышает допустимую длину.

    :param bot: экземпляр бота
    :param message: сообщение, на которое нужно ответить
    :param text: исходный текст, который нужно отправить
    :param max_length: максимальная длина сообщения (по умолчанию 4086 символов для Telegram)
    """
    # Разбиваем текст на части, если длина превышает max_length
    if len(text) <= max_length:
        bot.reply_to(message, text)
    else:
        # Разбиваем текст на части
        for i in range(0, len(text), max_length):
            part = text[i:i + max_length]
            bot.reply_to(message, part)