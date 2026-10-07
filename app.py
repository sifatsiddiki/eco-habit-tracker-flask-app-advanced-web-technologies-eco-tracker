from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eco.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    display_name = db.Column(db.String(80), nullable=True)
    badges = db.relationship('UserBadge', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=True)
    co2_saving = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    threshold = db.Column(db.Integer, default=0)  # e.g. days of streak

class UserBadge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    awarded_on = db.Column(db.Date, default=date.today)
    badge = db.relationship('Badge')

# Ensure database tables exist when the app starts
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# badge thresholds and names
BADGE_THRESHOLDS = [1,3,7,14,30,100]
BADGE_NAMES = {1:'First Step', 3:'3-Day Streak', 7:'1-Week Champion', 14:'2-Week Runner', 30:'Month Champion', 100:'Century Streak'}

def habit_streak(user_id, habit_id):
    today = date.today()
    streak = 0
    current_day = today
    while True:
        log = HabitLog.query.filter_by(user_id=user_id, habit_id=habit_id, date=current_day).first()
        if log:
            streak += 1
            current_day = current_day - timedelta(days=1)
        else:
            break
    return streak

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form.get('display_name','')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'warning')
            return redirect(url_for('register'))
        u = User(email=email, display_name=name)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(password):
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))
        login_user(u)
        flash('Logged in', 'success')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    habit_info = []
    total_co2 = 0.0
    for h in habits:
        s = habit_streak(current_user.id, h.id)
        logs_count = HabitLog.query.filter_by(user_id=current_user.id, habit_id=h.id).count()
        total_co2 += h.co2_saving * logs_count
        habit_info.append((h, s))
    # collect awarded badges with awarded_on
    user_badges = UserBadge.query.filter_by(user_id=current_user.id).all()
    badge_objs = [ub.badge for ub in user_badges]
    return render_template('dashboard.html', habit_info=habit_info, badges=badge_objs, total_co2=total_co2, user_badges=user_badges)

@app.route('/habit/add', methods=['GET','POST'])
@login_required
def add_habit():
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form.get('description','')
        co2 = float(request.form.get('co2_saving', '0') or 0)
        h = Habit(title=title, description=desc, co2_saving=co2, user_id=current_user.id)
        db.session.add(h)
        db.session.commit()
        flash('Habit added', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_habit.html')

@app.route('/habit/<int:habit_id>')
@login_required
def habit_detail(habit_id):
    h = Habit.query.get_or_404(habit_id)
    logs = HabitLog.query.filter_by(user_id=current_user.id, habit_id=habit_id).order_by(HabitLog.date.desc()).limit(30).all()
    s = habit_streak(current_user.id, habit_id)
    # determine next badge threshold
    next_threshold = None
    for t in BADGE_THRESHOLDS:
        if s < t:
            next_threshold = t
            break
    progress_pct = int((s / next_threshold) * 100) if next_threshold else 100
    return render_template('habit_detail.html', habit=h, logs=logs, streak=s, next_threshold=next_threshold, progress_pct=progress_pct)

@app.route('/habit/<int:habit_id>/log', methods=['POST'])
@login_required
def habit_log(habit_id):
    today = date.today()
    existing = HabitLog.query.filter_by(user_id=current_user.id, habit_id=habit_id, date=today).first()
    if existing:
        flash('Already logged today', 'info')
    else:
        hl = HabitLog(habit_id=habit_id, user_id=current_user.id, date=today)
        db.session.add(hl)
        db.session.commit()
        flash('Logged habit for today', 'success')
        # check badges
        s = habit_streak(current_user.id, habit_id)
        for t in BADGE_THRESHOLDS:
            if s == t:
                b = Badge.query.filter_by(threshold=t).first()
                if not b:
                    bname = BADGE_NAMES.get(t, f'{t}-day streak')
                    bdesc = f'Awarded for a {t}-day streak: {bname}'
                    b = Badge(name=bname, description=bdesc, threshold=t)
                    db.session.add(b)
                    db.session.commit()
                existing_award = UserBadge.query.filter_by(user_id=current_user.id, badge_id=b.id).first()
                if not existing_award:
                    ub = UserBadge(user_id=current_user.id, badge_id=b.id)
                    db.session.add(ub)
                    db.session.commit()
                    flash(f'Badge earned: {b.name}', 'success')
    return redirect(url_for('habit_detail', habit_id=habit_id))

@app.route('/feed')
@login_required
def feed():
    logs = HabitLog.query.order_by(HabitLog.date.desc()).limit(30).all()
    items = []
    for l in logs:
        habit = Habit.query.get(l.habit_id)
        items.append({'date': l.date, 'habit_title': habit.title if habit else 'Habit', 'user': f'User-{l.user_id}' })
    return render_template('feed.html', items=items)

@app.route('/init-db')
def init_db():
    db.create_all()
    return "DB initialized"



@app.route('/api/co2')
@login_required
def api_co2():
    # Return JSON mapping of habit titles to total co2 saved (co2_saving * number of logs)
    data = {}
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    for h in habits:
        logs_count = HabitLog.query.filter_by(user_id=current_user.id, habit_id=h.id).count()
        data[h.title] = round(h.co2_saving * logs_count, 3)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)