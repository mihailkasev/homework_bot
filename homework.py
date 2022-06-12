from settings import RETRY_TIME, ENDPOINT, HOMEWORK_STATUSES
import requests
import logging
import os
import time
import telegram
from http import HTTPStatus
import exceptions
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


def send_message(bot, message):
    """Отправка сообщения в бот Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Отправка сообщения')
    except telegram.TelegramError:
        message = 'Сбой при отправке сообщения в Telegram'
        logger.error(message)
        raise telegram.TelegramError(message)
    logger.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Запрос к единственному эндпоинту API-сервиса и возврат ответа API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logger.info('Запрос к API')
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except ConnectionError():
        message = 'Отсутствует подключение'
        logger.error(message)
        raise ConnectionError(message)
    if response.status_code != HTTPStatus.OK:
        message = 'Эндпоинт API-сервиса недоступен.'
        logger.error(message)
        raise exceptions.HTTPStatusCodeException(message)
    response = response.json()
    return response


def check_response(response):
    """Проверка ответа API на корректность."""
    if (not isinstance(response, dict)
            or not isinstance(response.get('homeworks'), list)):
        message = 'Неверный тип данных'
        logger.error(message)
        raise TypeError(message)
    else:
        return response.get('homeworks')


def parse_status(homework):
    """Извлечение из информации о домашней работе статуса этой работы."""
    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
    except KeyError():
        message = 'Отсутствие ожидаемых ключей в ответе API'
        logger.error(message)
        raise KeyError(message)
    if homework_status not in HOMEWORK_STATUSES:
        message = 'Недокументированный статус ответа'
        logger.error(message)
        raise KeyError(message)
    else:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    logger.info('Запуск бота')
    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                message = 'Пустой список'
                logger.error(message)
                raise exceptions.EmptyListException(message)
            else:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
                current_timestamp = response.get('current_date')
                time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != old_message:
                send_message(bot, message)
                old_message = message
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
