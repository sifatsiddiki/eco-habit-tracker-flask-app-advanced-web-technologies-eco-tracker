from app import db, User, Habit, HabitLog, Badge, UserBadge
from datetime import date, timedelta
db.create_all()
# create demo users
if not User.query.filter_by(email='student@example.com').first():
    u = User(email='student@example.com', display_name='Demo Student')
    u.set_password('password123')
    db.session.add(u)
    db.session.commit()
    # create habits for demo user
    h1 = Habit(title='Use public transport', description='Avoid car', co2_saving=0.5, user_id=u.id)
    h2 = Habit(title='Bring reusable bag', description='No plastic bags', co2_saving=0.1, user_id=u.id)
    db.session.add_all([h1,h2])
    db.session.commit()
    # create some logs for last 5 days
    for i in range(5):
        d = date.today() - timedelta(days=i)
        db.session.add(HabitLog(habit_id=h1.id, user_id=u.id, date=d))
    db.session.commit()
    # create sample badge and award one
    b3 = Badge(name='3-Day Streak', description='Achieved 3 day streak', threshold=3)
    db.session.add(b3)
    db.session.commit()
    ub = UserBadge(user_id=u.id, badge_id=b3.id)
    db.session.add(ub)
    db.session.commit()
print('Seed complete. User: student@example.com  password: password123')