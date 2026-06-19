"""Точка входа для serv00 / Passenger.

serv00 (как и многие shared-хостинги на Phusion Passenger) ищет объект
`application` в файле passenger_wsgi.py. Настройка домена на serv00:
  1. Создать веб-сайт с типом "Python" (или указать этот файл как точку входа).
  2. Установить зависимости: pip3.11 install --user -r requirements.txt
  3. Прописать переменные окружения (EBLOID_*) в ~/.bash_profile.
  4. Перезапустить приложение (touch tmp/restart.txt).
"""
import os
import sys

# Гарантируем, что интерпретатор видит наш пакет.
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app  # noqa: E402

application = create_app()

# Некоторые конфигурации Passenger ожидают имя `app`.
app = application
