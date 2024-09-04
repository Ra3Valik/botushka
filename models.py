from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from db import engine
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    chat_id = Column(String(255), nullable=False)
    nickname = Column(String(255), nullable=False)
    score = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint('user_id', 'chat_id', name='unique_user_chat'),)


class Chat(Base):
    __tablename__ = 'chats'

    chat_id = Column(String(255), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_positive = Column(Boolean, default=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship('User', back_populates='messages')


Base.metadata.create_all(engine)
