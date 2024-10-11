from app.models import User, Chat, Message
from config.db import session
import datetime
from lib.errors import log_error
from lib.helpers import format_date, get_case
from lib.classes.AutoRefreshTTLCache import user_cache
from app.bot_phrases import get_clear_chat_message, get_no_user_found_message, get_user_or_chat_no_found_message, get_no_messages_found_message
from sqlalchemy import func, case


def add_user(telegram_user_id, chat_id, username, score=0):
    """
    Добавляем пользователя в базу данных

    :param telegram_user_id:
    :param chat_id:
    :param username:
    :param score:
    :return:
    """
    try:
        user = User(telegram_user_id=telegram_user_id, chat_id=chat_id, username=username, score=score)
        session.add(user)
        session.commit()
    except Exception as e:
        session.rollback()
        log_error(e)


def update_user_score(chat_id, username, score=1):
    """
    Обновляем счёт пользователя

    :param chat_id:
    :param username:
    :param score:
    :return:
    """
    try:
        user = session.query(User).filter_by(username=username, chat_id=chat_id).first()
        user.score = user.score + score
        session.commit()
    except Exception as e:
        session.rollback()
        log_error(e)


def add_chat(chat_id, chat_name):
    """
    Добавляем чат в базу данных

    :param chat_id:
    :pararm chat_name
    :return:
    """
    try:
        chat = Chat(chat_id=chat_id, chat_name=chat_name)
        session.add(chat)
        session.commit()
    except Exception as e:
        session.rollback()
        log_error(e)


def check_user_exist(chat_id, username):
    """
    Проверяем знаем ли мы пользователя в этом чате по username

    :param chat_id:
    :param username:
    :return:
    """
    cache_key = f"user_exist_{chat_id}_{username}"
    result = user_cache.get(cache_key)

    if result is not None:
        return result

    try:
        user = session.query(User).filter_by(username=username, chat_id=chat_id).first()
        result = bool(user)

        if result:
            user_cache.set(cache_key, result)

        return result
    except Exception as e:
        session.rollback()
        log_error(e)


def check_user_exist_by_telegram_user_id(chat_id, telegram_user_id):
    """
    Проверяем знаем ли мы пользователя в этом чате по telegram_user_id

    :param chat_id:
    :param telegram_user_id:
    :return:
    """
    cache_key = f"user_exist_{chat_id}_{telegram_user_id}"
    result = user_cache.get(cache_key)

    if result is not None:
        return result

    try:
        user = session.query(User).filter_by(telegram_user_id=telegram_user_id, chat_id=chat_id).first()
        result = bool(user)

        if result:
            user_cache.set(cache_key, result)

        return result
    except Exception as e:
        session.rollback()
        log_error(e)


def clear_chat_score(chat_id):
    """
    Очищаем счёт пользователей

    :param chat_id:
    :return:
    """
    chat = session.query(Chat).filter_by(chat_id=chat_id).first()
    if chat:
        session.query(User).filter_by(chat_id=chat_id).update({User.score: 0})
        chat.last_reset = datetime.datetime.now()
        session.commit()
        return get_clear_chat_message()


def get_chat_ranking(chat_id):
    """
    Возвращает сообщеие с топом пользователей по Е-баллам

    :param chat_id:
    :return:
    """
    # Получить последний reset для данного чата
    chat = session.query(Chat).filter_by(chat_id=chat_id).first()
    last_reset = chat.last_reset if chat else None

    # Найти топ-10 пользователей по текущему количеству баллов
    users = session.query(User).filter_by(chat_id=chat_id).order_by(User.score.desc()).limit(10).all()

    if not users:
        return get_no_user_found_message()

    # Извлекаем ID пользователей из топ-10
    user_ids = [user.id for user in users]

    # Запрос на получение всех сообщений для этих пользователей после последней очистки, одним запросом
    messages_after_reset = session.query(
        Message.user_id,
        func.sum(case((Message.points > 0, Message.points), else_=0)).label("total_added"),
        func.sum(case((Message.points < 0, Message.points), else_=0)).label("total_subtracted")
    ).filter(
        Message.user_id.in_(user_ids),
        Message.created_at > last_reset if last_reset else True
    ).group_by(Message.user_id).all()

    # Преобразование сообщений в словарь для быстрого доступа
    messages_summary = {msg.user_id: (msg.total_added or 0, msg.total_subtracted or 0) for msg in messages_after_reset}

    # Формирование рейтинга
    ranking = []
    for idx, user in enumerate(users, start=1):
        # Извлекаем добавленные и отнятые баллы для текущего пользователя
        total_added, total_subtracted = messages_summary.get(user.id, (0, 0))

        score_word = get_case(user.score)

        ranking.append(
            f"{idx}. @{user.username} - текущее количество: {user.score} {score_word}; "
            f"\nДобавлено: +{total_added}; \nОтнято: {total_subtracted};"
        )

    return "\n".join(ranking)


def get_user_messages(chat_id, user_id):
    """
    Возвращает все сообщения начислений пользователя в чате, которые были отправлены после последней очистки (last_reset).

    :param chat_id:
    :param user_id:
    :return:
    """
    # Получаем чат и пользователя
    chat = session.query(Chat).filter_by(chat_id=chat_id).first()
    user = session.query(User).filter_by(id=user_id).first()

    if chat and user:
        # Фильтруем сообщения по дате, позже чем last_reset
        if chat.last_reset:
            messages = session.query(Message).filter(
                Message.user_id == user.id,
                Message.created_at > chat.last_reset
            ).order_by(Message.created_at.desc()).all()
        else:
            messages = session.query(Message).filter_by(user_id=user.id).order_by(Message.created_at.desc()).all()

        if messages:
            message_list = [
                f"{format_date(message.created_at)}: {'+{0}'.format(message.points) if message.points > 0 else f'{message.points}'} - {message.message if message.message and message.message.strip() else '**без комментария**'} от {message.from_username}"
                for message in messages]
            result = f"Общий счет пользователя: {user.score}"
            if message_list:
                result += f"\n\nИстория начисления:\n" + "\n".join(
                    message_list)
            return result
        else:
            return get_no_messages_found_message()
    else:
        return get_user_or_chat_no_found_message()


def get_all_user_messages(chat_id, user_id):
    """
    Возвращает все сообщения начислений пользователя в чате.
    Сообщения до last_reset выводятся отдельно и маркируются.

    :param chat_id:
    :param user_id:
    :return:
    """
    # Получаем чат и пользователя
    chat = session.query(Chat).filter_by(chat_id=chat_id).first()
    user = session.query(User).filter_by(chat_id=chat_id, id=user_id).first()

    if chat and user:
        # Сообщения после last_reset
        if chat.last_reset:
            recent_messages = session.query(Message).filter(
                Message.user_id == user.id,
                Message.created_at > chat.last_reset
            ).order_by(Message.created_at.desc()).all()

            # Сообщения до last_reset
            older_messages = session.query(Message).filter(
                Message.user_id == user.id,
                Message.created_at <= chat.last_reset
            ).order_by(Message.created_at.desc()).all()
        else:
            # Если очистка не производилась, просто берем все сообщения
            recent_messages = session.query(Message).filter_by(user_id=user.id).order_by(
                Message.created_at.desc()).all()
            older_messages = []

        # Формируем вывод сообщений
        recent_message_list = [
            f"{format_date(message.created_at)}: {'+{0}'.format(message.points) if message.points > 0 else f'{message.points}'} - {message.message if message.message and message.message.strip() else '**без комментария**'} от {message.from_username}"
            for message in recent_messages]
        older_message_list = [
            f"{format_date(message.created_at)}: {'+{0}'.format(message.points) if message.points > 0 else f'{message.points}'} - {message.message if message.message and message.message.strip() else '**без комментария**'} от {message.from_username}"
            for message in older_messages]

        result = f"Общий счет пользователя: {user.score}\n"
        if recent_message_list:
            result += "История начисления:\n" + "\n".join(recent_message_list)

        if older_message_list:
            result += "\n\n--- Сообщения до последней очистки ---\n"
            result += "\n".join(older_message_list)

        return result
    else:
        return get_user_or_chat_no_found_message()


def add_message(chat_id, telegram_user_id, message_text, from_username, points):
    """
    Добавляет сообщение для пользователя в чате.

    :param chat_id: в каком чате
    :param telegram_user_id: кому
    :param message_text: сообщение
    :param from_username: от кого
    :param points: кол-во очков
    :return:
    """
    # Получаем пользователя в указанном чате
    user = session.query(User).filter_by(chat_id=chat_id, telegram_user_id=telegram_user_id).first()

    # Если пользователь существует, добавляем сообщение
    if user:
        new_message = Message(
            user_id=user.id,
            points=points,
            message=message_text,
            from_username=from_username
        )

        # Добавляем новое сообщение в сессию и сохраняем
        session.add(new_message)
        session.commit()


def get_user_id_from_username(chat_id, username):
    """
    Возвращает user_id по имени пользователя в указанном чате.

    :param chat_id:
    :param username:
    :return:
    """
    cache_key = f"user_id_{chat_id}_{username}"
    user_id = user_cache.get(cache_key)

    if user_id:
        return user_id

    user = session.query(User).filter_by(chat_id=chat_id, username=username).first()
    user_id = user.id if user else None

    if user_id:
        user_cache.set(cache_key, user_id)

    return user_id


def get_telegram_user_id_from_username(chat_id, username):
    """
    Возвращает telegram_user_id по имени пользователя в указанном чате.

    :param chat_id:
    :param username:
    :return:
    """
    cache_key = f"telegram_user_id_{chat_id}_{username}"
    telegram_user_id = user_cache.get(cache_key)

    if telegram_user_id:
        return telegram_user_id

    user = session.query(User).filter_by(chat_id=chat_id, username=username).first()
    telegram_user_id = user.telegram_user_id if user else None

    if telegram_user_id:
        user_cache.set(cache_key, telegram_user_id)

    return telegram_user_id


def check_chat_exist(chat_id):
    """
    Проверка на существование чата в бд

    :param chat_id:
    :return:
    """
    cache_key = f"is_chat_exist_{chat_id}"
    chat_exists = user_cache.get(cache_key)

    if chat_exists:
        return True

    chat = session.query(Chat).filter_by(chat_id=chat_id).first()
    is_exists = True if chat else False

    if is_exists:
        user_cache.set(cache_key, True)

    return is_exists


def can_manage_chat(chat_id, telegram_user_id, bot):
    """
    Проверяем может ли пользователь управлять группой

    :param chat_id:
    :param telegram_user_id:
    :param bot: Чтобы понять является ли админом
    :return:
    """
    cache_key = f"can_manage_chat_{chat_id}_{telegram_user_id}"
    cache_value = user_cache.get(cache_key)

    if cache_value:
        return True

    user = session.query(User).filter_by(chat_id=chat_id, telegram_user_id=telegram_user_id).first()
    if user.is_manager:
        user_cache.set(cache_key, True)
        return True
    admins = bot.get_chat_administrators(chat_id)
    for admin in admins:
        if admin.user.id == telegram_user_id:
            user_cache.set(cache_key, True)
            return True
    return False


def can_add_multiple_points(chat_id, telegram_user_id, bot):
    """
    Проверяем или пользователь может добавлять несколько баллов

    :param chat_id:
    :param telegram_user_id:
    :param bot:
    :return:
    """
    cache_key = f"chat_send_few_carma_{chat_id}"
    setting = user_cache.get(cache_key)

    if setting == 'all':
        return True

    chat = session.query(Chat).filter_by(chat_id=chat_id).first()
    if chat.send_few_carma == 'all':
        user_cache.set(cache_key, 'all')
        return True
    return can_manage_chat(chat_id, telegram_user_id, bot)


def get_telegram_user_id_by_user_id(user_id):
    """
    Взять telegram_user_id зная его id

    :param user_id: id пользоваталея в базе данных
    :return: telegram_user_id
    """
    cache_key = f"get_telegram_user_id_by_user_id_{user_id}"
    telegram_user_id = user_cache.get(cache_key)
    if telegram_user_id:
        return telegram_user_id
    user = session.query(User).filter_by(id=user_id).first()
    user_cache.set(cache_key, user.telegram_user_id)
    return user.telegram_user_id