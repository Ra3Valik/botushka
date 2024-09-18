from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lib.helpers import env_variables

import pymysql

pymysql.install_as_MySQLdb()

username = env_variables.get('DB_USERNAME')
password = env_variables.get('DB_PASSWORD')
host = env_variables.get('DB_HOST')
port = env_variables.get('DB_PORT')
db_name = env_variables.get('DB_NAME')

DATABASE_URL = f"mysql+pymysql://{username}:"
if password:
    DATABASE_URL += password
DATABASE_URL += f"@{host}"
if port:
    DATABASE_URL += f":{port}"
DATABASE_URL += f"/{db_name}?charset=utf8mb4"

# Создаем соединение с базой данных MySQL
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Создаем сессию
Session = sessionmaker(bind=engine)
session = Session()