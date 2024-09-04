from models import User, Chat
from db import session


def add_user(user_id, chat_id, nickname, score=0):
    try:
        user = User(user_id=user_id, chat_id=chat_id, nickname=nickname, score=score)
        session.add(user)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Failed to add user: {e}")


def update_user_score(nickname, chat_id, score = 1):
    try:
        user = session.query(User).filter_by(nickname=nickname, chat_id=chat_id).first()
        user.score = user.score + score
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Failed to update score: {e}")


def add_chat(chat_id):
    try:
        chat = Chat(chat_id=chat_id)
        session.add(chat)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Failed to add chat: {e}")


def check_user_exist(nickname, chat_id):
    try:
        user = session.query(User).filter_by(nickname=nickname, chat_id=chat_id).first()
        return bool(user)
    except Exception as e:
        session.rollback()
        print(f"Failed when user existing check: {e}")
