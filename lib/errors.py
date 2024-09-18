import logging

logging.basicConfig(
    level=logging.ERROR,  # Уровень логирования
    format='[%(asctime)ы] - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app_errors.log", encoding='utf-8'),  # Запись логов в файл
        logging.StreamHandler()  # Вывод логов в консоль
    ]
)

formatter = logging.Formatter('[%(asctime)s] - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
for handler in logging.getLogger().handlers:
    handler.setFormatter(formatter)

logger = logging.getLogger(__name__)


def log_error(error_message):
    logger.error(error_message)
