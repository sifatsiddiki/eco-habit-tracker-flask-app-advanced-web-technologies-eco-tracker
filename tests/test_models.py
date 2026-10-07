import pytest
from datetime import date, timedelta
from app import app, db, User, Habit, HabitLog
from werkzeug.security import generate_password_hash

@pytest.fixture
def app_context():
    app.config["TESTING"] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield

def test_create_user_and_habit(app_context):
    user = User(
        email="modeluser@example.com",
        display_name="Model User",
        password_hash=generate_password_hash("secret123"),
    )
    db.session.add(user)
    db.session.commit()

    habit = Habit(
        name="Walk instead of drive",
        description="Walk short distances instead of using a car",
        co2_saving_per_action=0.5,
        user_id=user.id,
    )
    db.session.add(habit)
    db.session.commit()

    assert habit.id is not None
    assert habit.user_id == user.id

def test_habit_log_and_streak_like_behaviour(app_context):
    user = User(
        email="streak@example.com",
        display_name="Streak User",
        password_hash=generate_password_hash("secret123"),
    )
    db.session.add(user)
    db.session.commit()

    habit = Habit(
        name="Use reusable bottle",
        description="Avoid buying plastic bottles",
        co2_saving_per_action=0.2,
        user_id=user.id,
    )
    db.session.add(habit)
    db.session.commit()

    today = date.today()
    yesterday = today - timedelta(days=1)

    log1 = HabitLog(habit_id=habit.id, user_id=user.id, date=yesterday)
    log2 = HabitLog(habit_id=habit.id, user_id=user.id, date=today)

    db.session.add_all([log1, log2])
    db.session.commit()

    logs = HabitLog.query.filter_by(habit_id=habit.id).all()
    assert len(logs) == 2