from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import User, Chat
from config.db import session
from app.bot_phrases import get_user_no_chats_message, get_user_odd_point_message, get_user_add_point_message
from lib.crud import update_user_score, add_message, get_telegram_user_id_by_user_id
from lib.state import awaiting_count_of_point
from lib.functions import send_self_mention_message
from lib.classes.AutoRefreshTTLCache import user_cache
import re


def bot_keyboard_buttons_handler(call, bot):
    """
    Перехват всех действий кнопок и распеределение их по функциям

    :param call:
    :param bot:
    :return:
    """
    action = call.data
    match action:
        case 'chats':
            action_chats(call, bot)
        case 'aodd':
            chat_for_adding_points(call, bot)
        case 'smch':
            edit_managers(call, bot)

    match call.data:
        # Сопоставление с префиксом для настроек чата
        case action if action.startswith('cs_a_') or action.startswith('cs_m_'):
            set_chat_settings(call, bot)

        case action if action.startswith('cs_'):
            chat_settings(call, bot)

        # Сопоставление для управления действиями менеджеров
        case action if action.startswith('wm_'):
            view_all_managers(call, bot)

        case action if action.startswith('em_'):
            select_action_with_managers(call, bot)

        case action if action.startswith('dm_') or action.startswith('am'):
            select_managers_message(call, bot)

        case action if action.startswith('fdm_') or action.startswith('fam'):
            managers_action(call, bot)

        # Сопоставление для изменения баллов пользователей
        case action if action.startswith('ap_'):
            select_user_for_changing_points(call, bot)

        case action if action.startswith('fap_'):
            wait_user_points_changing(call, bot)

    bot.answer_callback_query(call.id)  # Сообщаем Telegram, что запрос был обработан


def get_settings_keyboard_markup():
    """
    Кнопки действий
    
    :return: 
    """
    markup = InlineKeyboardMarkup()

    button1 = InlineKeyboardButton("Настройки чатов", callback_data='chats')
    button2 = InlineKeyboardButton("Изменение Е-баллов", callback_data='aodd')
    button3 = InlineKeyboardButton("Менеджеры чата", callback_data='smch')

    markup.add(button1)
    markup.add(button2)
    markup.add(button3)

    return markup


def get_managers_keyboard_markup(chat_id):
    """
    Кнопки действий с менеджерами
    
    :param chat_id: 
    :return: 
    """
    markup = InlineKeyboardMarkup()

    button1 = InlineKeyboardButton("Убрать менеджеров", callback_data=f"dm_{chat_id}")
    button2 = InlineKeyboardButton("Добавить менеджера", callback_data=f"am_{chat_id}")
    button3 = InlineKeyboardButton("Просмотр менеджеров", callback_data=f"wm_{chat_id}")

    markup.add(button1)
    markup.add(button2)
    markup.add(button3)

    return markup


def get_group_settings_keyboard_markup(chat_id):
    """
    Кнопки с выбором, кто может отправлять неединичное количество Е-баллов
    
    :param chat_id: 
    :return: 
    """
    markup = InlineKeyboardMarkup()

    button1 = InlineKeyboardButton("Все", callback_data=f"cs_a_{chat_id}")
    button2 = InlineKeyboardButton("Менеджеры чата", callback_data=f"cs_m_{chat_id}")

    markup.add(button1, button2)

    return markup


def get_chats_keyboard_markup(telegram_user_id, func_name, bot, should_be_manager=False):
    """
    Все чаты пользователя
    
    :param telegram_user_id: 
    :param func_name: Префикс по которому мы определяем что делать
    :param bot: 
    :param should_be_manager: Если нужно выбрать чаты где пользователь является менеджером или администратором
    :return: 
    """
    if should_be_manager:
        all_user_chats = session.query(Chat, User).join(User, User.chat_id == Chat.chat_id).filter(
            User.telegram_user_id == telegram_user_id).all()
        user_chats = []
        for chat, user in all_user_chats:
            if user.is_manager:
                user_chats.append(chat)
                continue
            admins = bot.get_chat_administrators(chat.chat_id)
            for admin in admins:
                if admin.user.id == telegram_user_id:
                    user_chats.append(chat)
                    continue

    else:
        user_chats = session.query(Chat).join(User, User.chat_id == Chat.chat_id).filter(
            User.telegram_user_id == telegram_user_id).all()
    if user_chats:
        markup = InlineKeyboardMarkup()
        for chat in user_chats:
            button = InlineKeyboardButton(text=chat.chat_name, callback_data=f"{func_name}_{chat.chat_id}")
            markup.add(button)

        return markup
    else:
        return False


def get_users_keyboard_markup(chat_id, is_manager, func_name, exclude_user_id=None, all_users=False):
    """
    Выводит пользователей чата

    :param chat_id: ID чата
    :param is_manager: Должны ли пользователи быть менеджерами?
    :param func_name: Префикс для callback_data
    :param exclude_user_id: ID пользователя, которого нужно исключить
    :param all_users: Вывести всех пользователей
    :return: InlineKeyboardMarkup или False
    """
    if all_users:
        users = session.query(User).filter_by(chat_id=chat_id).all()
    else:
        users = session.query(User).filter_by(chat_id=chat_id, is_manager=is_manager).all()

    if exclude_user_id:
        users = [user for user in users if str(user.telegram_user_id) != str(exclude_user_id)]

    if users:
        markup = InlineKeyboardMarkup()
        for user in users:
            button = InlineKeyboardButton(text=user.username, callback_data=f"{func_name}_{user.id}")
            markup.add(button)
        return markup
    else:
        return False


def action_chats(call, bot):
    select_chat_message(call, bot, 'cs', True)


def chat_settings(call, bot):
    """
    Сообщение с выбором настроек чата
    
    :param call: 
    :param bot: 
    :return: 
    """
    chat_id = call.data[3:]
    markup = get_group_settings_keyboard_markup(chat_id)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Кто может отправлять любое количество Е-баллов?', reply_markup=markup)


def set_chat_settings(call, bot):
    """
    Применяем настройку "Кто может отправлять любое количество Е-баллов?" для чата
    
    :param call: 
    :param bot: 
    :return: 
    """
    chat_id = call.data[5:]
    chat = session.query(Chat).filter_by(chat_id=chat_id).first()
    cache_key = f"chat_send_few_carma_{chat_id}"

    if call.data.startswith('cs_a_'):
        chat.send_few_carma = 'all'
        user_cache.set(cache_key, 'all')
    elif call.data.startswith('cs_m_'):
        chat.send_few_carma = 'managers'
        user_cache.set(cache_key, 'managers')
    session.commit()
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Настройки чата изменены!')


def edit_managers(call, bot):
    """
    Выбор чата для действий с менеджерами
    
    :param call: 
    :param bot: 
    :return: 
    """
    select_chat_message(call, bot, 'em', True)


def select_action_with_managers(call, bot):
    """
    Выбор действия которое вы хотите применить к менеджерам
    
    :param call: 
    :param bot: 
    :return: 
    """
    chat_id = call.data[3:]
    markup = get_managers_keyboard_markup(chat_id)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Выберите действие:', reply_markup=markup)


def select_managers_message(call, bot):
    """
    Выберите пользователя которого хотите добавить в менеджеры или удалить из менеджеров
    
    :param call: 
    :param bot: 
    :return: 
    """
    action = call.data
    chat_id = action[3:]
    current_user_id = call.from_user.id
    if action.startswith('am_'):
        markup = get_users_keyboard_markup(chat_id, False, 'fam', current_user_id)
        if not markup:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='Нет пользователей которых можно сделать менеджерами.')
            return
        message_text = 'Выберите пользователя, которого хотите сделать менеджером:'
    elif action.startswith('dm_'):
        markup = get_users_keyboard_markup(chat_id, True, 'fdm', current_user_id)
        if not markup:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Нет менеджеров.')
            return
        message_text = 'Выберите менеджера, которого хотите удалить из списка:'

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=message_text, reply_markup=markup)


def managers_action(call, bot):
    """
    Делаем пользователя менеджером или удаляем из них
    
    :param call: 
    :param bot: 
    :return: 
    """
    action = call.data
    user_id = action[4:]
    user = session.query(User).filter_by(id=user_id).first()

    if action.startswith('fam_'):
        user.is_manager = True
        message_text = f"{user.username} теперь менеджер!"
    elif action.startswith('fdm_'):
        user.is_manager = False
        message_text = f"{user.username} больше не является менеджером"
    session.commit()
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=message_text)

def chat_for_adding_points(call, bot):
    """
    Выбор чата в котором надо добавить Е-баллы

    :param call:
    :param bot:
    :return:
    """
    select_chat_message(call, bot, 'ap', True)

def select_user_for_changing_points(call, bot):
    """
    Выбор пользователя которому добавляют/отнимают карму

    :param call:
    :param bot:
    :return:
    """
    chat_id = call.data[3:]
    current_user_id = call.from_user.id
    markup = get_users_keyboard_markup(chat_id, False, 'fap', current_user_id, True)
    if not markup:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='Нет пользователей в этом чате.')
        return
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Выберите пользователя для добавления баллов', reply_markup=markup)


def wait_user_points_changing(call, bot):
    """
    Уведомления пользователя о том, что мы ждём на сколько изменить Е-баллы

    :param call:
    :param bot:
    :return:
    """
    user_id = call.data[4:]
    telegram_user_id = get_telegram_user_id_by_user_id(user_id)
    self_mention = call.from_user.username if str(telegram_user_id) == str(call.from_user.id) else None
    if self_mention and self_mention != 'Ra3Valik':
        send_self_mention_message(bot, call.message, self_mention)
        return

    awaiting_count_of_point[call.message.chat.id] = user_id
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Введите количество баллов и сообщение (необязательно): ")


def maybe_change_points(message, user_id, bot):
    """
    Изменение баллов пользователя

    :param message:
    :param user_id:
    :param bot:
    :return:
    """
    user = session.query(User).filter_by(id=user_id).first()

    pattern = r"^([+-]?\d+|--|\+\+|—)\s*(.*)"

    # Поиск числа и текста
    match = re.match(pattern, message.text.strip())

    if match:
        number_str = match.group(1) or '0'
        text = match.group(2) or ''

        if number_str == '0':
            awaiting_count_of_point[message.chat.id] = user_id
            bot.reply_to(message, 'Что-то пошло не так, введите количество Е-баллов в формате: +(-)n message\n'
                                  'Где n - количество баллов которые надо добавить или отнять\n'
                                  'message - сообщение которое хотите добавить при изменении баллов (необязательно)\n\n'
                                  'Попробуйте ещё раз!')
            return

        if number_str == '++':
            number = 1
        elif number_str in ['--', '—']:
            number = -1
        else:
            number = int(number_str)

        if number >= 0:
            bot.reply_to(message, get_user_add_point_message(user.username, number))
        else:
            bot.reply_to(message, get_user_odd_point_message(user.username, number))

        # Обновление баллов и добавление записи в историю
        update_user_score(user.chat_id, user.username, number)
        add_message(user.chat_id, user.telegram_user_id, text, message.from_user.username, number)
    else:
        awaiting_count_of_point[message.chat.id] = user_id
        bot.reply_to(message, 'Что-то пошло не так, введите количество Е-баллов в формате: +(-)n message\n'
                              'Где n - количество баллов которые надо добавить или отнять\n'
                              'message - сообщение которое хотите добавить при изменении баллов (необязательно)\n\n'
                              'Попробуйте ещё раз!')


def select_chat_message(call, bot, prefix, should_be_manager):
    """
    Вывод сообщения с выбором чата
    
    :param call: 
    :param bot: 
    :param prefix: Префикс по которому мы определяем что делать
    :param should_be_manager: Если надо вывести только те чаты, где пользователь имеет права
    :return: 
    """
    telegram_user_id = call.from_user.id
    markup = get_chats_keyboard_markup(telegram_user_id, prefix, bot, should_be_manager)
    if markup:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='Выберите чат:', reply_markup=markup)
    else:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=get_user_no_chats_message())


def view_all_managers(call, bot):
    """
    Выводит администраторов и менеджеров чата

    :param call:
    :param bot:
    :return:
    """
    action = call.data
    chat_id = action[3:]
    chat = session.query(Chat).filter_by(chat_id=chat_id).first()

    if 'all' == chat.send_few_carma:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='В этом чате включен режим без менеджеров!')
    else:
        # Получаем администраторов чата
        admins = bot.get_chat_administrators(chat_id)
        admin_list = [f"{admin.user.username or 'нет ника'}" for admin in admins]
        admin_ids = [admin.user.id for admin in admins]

        # Получаем менеджеров и исключаем администраторов
        managers = session.query(User).filter_by(chat_id=chat_id, is_manager=True).all()
        managers = [manager for manager in managers if manager.id not in admin_ids]
        manager_list = [f"{manager.username}" for manager in managers]

        # Формируем текст сообщения
        message_text = "Администраторы чата:\n" + '\n'.join(admin_list) + "\n\nМенеджеры чата:\n"
        if manager_list:
            message_text += '\n'.join(manager_list)
        else:
            message_text += "Нет менеджеров."

        # Обновляем сообщение в чате
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=message_text)
