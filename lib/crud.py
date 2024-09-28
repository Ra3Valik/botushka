from app.models import User, Chat, Message
from config.db import session
import datetime
from lib.errors import log_error
from lib.helpers import format_date, get_case
from lib.classes.AutoRefreshTTLCache import user_cache


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


def add_chat(chat_id):
    """
    Добавляем чат в базу данных

    :param chat_id:
    :return:
    """
    try:
        chat = Chat(chat_id=chat_id)
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
        return "Теперь у всех очищены Е-баллы"


def get_chat_ranking(chat_id):
    """
    Возвращает сообщеие с топом пользователей по Е-баллам

    :param chat_id:
    :return:
    """
    users = session.query(User).filter_by(chat_id=chat_id).order_by(User.score.desc()).limit(10).all()

    if not users or users[0].score == 0:
        return "В чате пока нет E-балльников."

    ranking = []
    for idx, user in enumerate(users, start=1):
        score_word = get_case(user.score)
        ranking.append(f"{idx}. @{user.username} - {user.score} {score_word}")

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
                f"{format_date(message.created_at)}: {str(message.points)} - {message.message if message.message.strip() else '**без комментария**'} от {message.from_username}"
                for message in messages]
            result = f"Общий счет пользователя: {user.score}"
            if message_list:
                result += f"\n\nИстория начисления:\n" + "\n".join(
                    message_list)
            return result
        else:
            return "Нет сообщений после последней очистки."
    else:
        return "Пользователь или чат не найдены."


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
            f"{format_date(message.created_at)}: {str(message.points)} - {message.message if message.message.strip() else '**без комментария**'} от {message.from_username}"
            for message in recent_messages]
        older_message_list = [
            f"{format_date(message.created_at)}: {str(message.points)} - {message.message if message.message.strip() else '**без комментария**'} от {message.from_username}"
            for message in older_messages]

        result = f"Общий счет пользователя: {user.score}\n"
        if recent_message_list:
            result += "История начисления:\n" + "\n".join(recent_message_list)

        if older_message_list:
            result += "\n\n--- Сообщения до последней очистки ---\n"
            result += "\n".join(older_message_list)

        return result
    else:
        return "Пользователь или чат не найдены."


def add_message(chat_id, telegram_user_id, message_text, from_username, points):
    """
    Добавляет сообщение для пользователя в чате.

    :param from_username:
    :param chat_id:
    :param telegram_user_id:
    :param message_text:
    :param points:
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


def get_user_id_from_nickname(chat_id, username):
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


def can_manage_chat(chat_id, telegram_user_id):
    """
    Проверяем является ли пользователь менеджером группы

    :param chat_id:
    :param user_id:
    :return:
    """