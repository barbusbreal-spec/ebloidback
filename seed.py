"""Наполнение базы демо-данными: python seed.py

Создаёт администратора-разработчика и пару опубликованных приложений,
чтобы магазин не был пустым при первом запуске.
"""
from app import create_app
from app.models import App, Review, STATUS_APPROVED, Screenshot, User, db

app = create_app()

with app.app_context():
    if not User.query.filter_by(username="demo").first():
        dev = User(username="demo", email="demo@ebloid.dev",
                   display_name="Demo Studio", is_developer=True)
        dev.set_password("demo123")
        db.session.add(dev)
        db.session.flush()

        samples = [
            dict(package_name="com.ebloid.notes", title="Ebloid Notes",
                 short_description="Быстрые заметки и списки",
                 description="Минималистичный блокнот с синхронизацией.",
                 category="Инструменты", version="1.2"),
            dict(package_name="com.ebloid.runner", title="Pixel Runner",
                 short_description="Аркадный раннер",
                 description="Беги, прыгай, собирай монеты. Бесконечный раннер.",
                 category="Игры", version="2.0"),
            dict(package_name="com.ebloid.weather", title="Погода Сегодня",
                 short_description="Точный прогноз погоды",
                 description="Погода на 7 дней, радар осадков, виджеты.",
                 category="Прочее", version="3.1"),
        ]
        for s in samples:
            a = App(developer_id=dev.id, status=STATUS_APPROVED, downloads=120, **s)
            db.session.add(a)
            db.session.flush()
            db.session.add(Review(app_id=a.id, user_id=dev.id, rating=5,
                                  text="Отличное приложение!"))

        db.session.commit()
        print("Демо-данные созданы. Логин разработчика: demo / demo123")
    else:
        print("Демо-данные уже существуют.")
