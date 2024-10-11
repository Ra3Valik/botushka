from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from config.db import engine
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(String(255), nullable=False)
    chat_id = Column(String(255), nullable=False)
    is_manager = Column(Boolean, default=False)
    username = Column(String(255), nullable=False)
    score = Column(Integer, default=0)

    messages = relationship('Message', back_populates='user')

    __table_args__ = (UniqueConstraint('telegram_user_id', 'chat_id', name='unique_user_chat'),)


class Chat(Base):
    __tablename__ = 'chats'

    chat_id = Column(String(255), primary_key=True)
    chat_name = Column(String(255), nullable=True)
    send_few_carma = Column(String(255), nullable=False, default='all')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_reset = Column(DateTime, nullable=True)


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    points = Column(Integer, nullable=False)
    message = Column(Text, nullable=True)
    from_username = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship('User', back_populates='messages')


Base.metadata.create_all(engine)
