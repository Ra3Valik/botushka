import random
from lib.helpers import get_case

user_not_found = [
    'Е-балльник @$nickname$ не найден в этом чате :(\nПускай только покажется в этом чате!',
    'Да кто такой этот ваш $nickname$?!\nПокажись! Кто бы ты не был.'
]

user_add_points = [
    '$nickname$ получил $count$ $case$!',
    '$nickname$ теперь имеет на $count$ $case$ больше!',
    '$nickname$, поздравляю! Тебе начислено $count$ $case$!',
    '$nickname$ теперь в плюсе на $count$ $case$!',
    '$nickname$ заработал $count$ $case$! Отлично!',
]

user_odd_points = [
    '$nickname$ потерял $count$ $case$. Надеюсь, всё не так плохо.',
    '$nickname$, минус $count$ $case$. Постарайся больше не повторять!',
    '$nickname$ снижено количество $case$ на $count$. Будь осторожнее!',
    '$nickname$ уменьшилось количество $case$ на $count$. Исправим это!',
    '$nickname$, у тебя убрали $count$ $case$. Работай над собой!',
]


def get_user_not_found_message(username):
    return random.choice(user_not_found).replace('$nickname$', username)


def get_user_add_point_message(username, count):
    case = get_case(count)
    count_word = str(count)
    return random.choice(user_add_points).replace('$nickname$', username).replace('$count$', count_word).replace(
        '$case$', case)


def get_user_odd_point_message(username, count):
    case = get_case(count)
    count_word = str(count)
    return random.choice(user_odd_points).replace('$nickname$', username).replace('$count$', count_word).replace(
        '$case$', case)
