"""Точка входа для serv00 / Passenger.

serv00 (как и многие shared-хостинги на Phusion Passenger) ищет объект
`application` в этом файле.

ВАЖНО про окружение: Passenger часто запускает приложение «системным» Python,
в котором НЕ установлены наши зависимости (Flask и т.д.) — из-за этого появляется
страница «Web application could not be started». Чтобы этого избежать, ниже мы
автоматически переключаемся на интерпретатор из виртуального окружения.

Рекомендуемая установка на serv00:
  cd ~/ebloidback
  python3.11 -m venv venv
  ./venv/bin/pip install -r requirements.txt
  mkdir -p tmp && touch tmp/restart.txt

Если venv лежит в другом месте — укажите путь в переменной EBLOID_VENV.
Если запуск всё равно падает — откройте сайт в браузере: вместо общей ошибки
Passenger будет показан настоящий traceback (его же можно увидеть в логах serv00).
"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _maybe_switch_to_venv():
    """Перезапускает процесс под интерпретатором виртуального окружения.

    Сравнение путей идёт БЕЗ resolve символлинков: venv определяется именно по
    пути к python (рядом лежит pyvenv.cfg), поэтому realpath использовать нельзя —
    иначе можно зациклиться или не активировать venv.
    """
    candidates = []
    if os.environ.get("EBLOID_VENV"):
        candidates.append(os.environ["EBLOID_VENV"])
    candidates += [os.path.join(HERE, "venv"), os.path.join(HERE, ".venv")]

    # Уже работаем внутри одного из этих venv? Тогда ничего не делаем.
    for venv in candidates:
        if os.path.abspath(venv) == os.path.abspath(sys.prefix):
            return

    for venv in candidates:
        interp = os.path.join(venv, "bin", "python3")
        if not os.path.exists(interp):
            interp = os.path.join(venv, "bin", "python")
        if os.path.exists(interp) and os.path.abspath(sys.executable) != os.path.abspath(interp):
            try:
                os.execl(interp, interp, *sys.argv)
            except OSError:
                pass  # не вышло — продолжаем на текущем интерпретаторе
            return


_maybe_switch_to_venv()

try:
    from app import create_app

    application = create_app()
except Exception:  # noqa: BLE001 — нужно показать любую ошибку запуска
    _startup_error = traceback.format_exc()

    def application(environ, start_response):
        body = (
            "EbloidStore: приложение не смогло запуститься.\n\n"
            f"Python: {sys.executable}\n"
            f"sys.path[0]: {sys.path[0]}\n\n"
            "Traceback:\n"
            f"{_startup_error}\n"
            "Подсказка: чаще всего это значит, что зависимости не установлены в том\n"
            "окружении, которым Passenger запускает приложение. Создайте venv и\n"
            "поставьте requirements (см. комментарий в начале passenger_wsgi.py)."
        )
        start_response("500 Internal Server Error",
                       [("Content-Type", "text/plain; charset=utf-8")])
        return [body.encode("utf-8")]

# Некоторые конфигурации Passenger ожидают имя `app`.
app = application
