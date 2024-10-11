import os


def load_env_file(filepath):
    """
    Считывание файла в переменную

    :param filepath:
    :return:
    """
    env_vars = {}
    abs_path = os.path.abspath(filepath)
    with open(abs_path, "r") as file:
        for line in file:
            # Игнорируем комментарии и пустые строки
            if line.startswith('#') or not line.strip():
                continue

            # Парсим строку в формате KEY=VALUE
            key, value = line.strip().split('=', 1)
            env_vars[key] = value
    return env_vars


env_variables = load_env_file(".env")


def is_integer(num):
    """
    Проверка является ли переданное целым числом

    :param num:
    :return:
    """
    try:
        if num is None:
            return False
        int(num)
        return True
    except ValueError:
        return False


MONTHS_RU = {
    1: 'Января', 2: 'Февраля', 3: 'Марта', 4: 'Апреля', 5: 'Мая', 6: 'Июня',
    7: 'Июля', 8: 'Августа', 9: 'Сентября', 10: 'Октября', 11: 'Ноября', 12: 'Декабря'
}


def format_date(date):
    """
    Дата в формате '%d %B %Y'

    :param date:
    :return:
    """
    day = date.day
    month = MONTHS_RU[date.month]
    year = date.year
    return f"{day} {month} {year}"


def get_case(count):
    """
    Склоняем слово Е-балл в зависимости от кол-ва

    :param count:
    :return:
    """
    if count == 1 or count == -1:
        return "Е-балл"
    elif count in [2, 3, 4, -2, -3, -4]:
        return "Е-балла"
    else:
        return "Е-баллов"
