import datetime

from flask import Flask, render_template, redirect, request, make_response, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_restful import Api
# from sqlalchemy import or_
from flask_wtf import FlaskForm
from werkzeug.exceptions import abort
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired

import news_resources
from data import db_session
from data.news import News
from data.users import User
from help_functions import check_password

app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=365)
login_manager = LoginManager()
login_manager.init_app(app)


class BaseForm(FlaskForm):
    background = 'https://avatars.mds.yandex.net/get-pdb/1947635/6706b408-eb97-49ce-9133-cf95447c9301/s1200'
    light_dark = 'white'
    back = '#0a0a0a'


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя пользователя', validators=[DataRequired()])
    about = TextAreaField("Немного о себе")
    submit = SubmitField('Войти')


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class NewsForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired()])
    content = TextAreaField("Содержание")
    is_private = BooleanField("Личное")
    submit = SubmitField('Применить')


class ProfileForm(FlaskForm):
    name = 'User'
    user = current_user
    cur_user = current_user
    friends = [current_user]
    error = ''


class UsersForm(FlaskForm):
    find_string = StringField('Поиск', validators=[DataRequired()])
    submit = SubmitField('Найти')


class SettingForm(FlaskForm):
    avatar = StringField('Смена аватара')
    name = StringField('Смена ника')
    status = StringField('Смена статуса')
    background = StringField('Смена заднего фона')
    theme = BooleanField("Тёмная\светлая тема")
    submit = SubmitField('Применить')


def get_base():
    base = BaseForm()
    base.background = current_user.background
    base.light_dark = 'white' if not current_user.theme else 'black'
    base.back = '#0a0a0a' if not current_user.theme else '#f5f5f5'
    return base


@app.route('/add_friend/<int:user_id>', methods=['GET', 'POST'])
def add_friend(user_id):
    if user_id != current_user.id:
        session = db_session.create_session()
        user = session.query(User).filter(User.id == current_user.id).first()
        if ', ' not in user.friends and current_user.friends == '':
            user.friends = "'" + str(user_id) + "'"
        elif ', ' not in user.friends and current_user.friends != '':
            user.friends = "'" + user.friends.strip("'") + ', ' + str(user_id) + "'"
        else:
            user.friends = user.friends[:-1] + ', ' + str(user_id) + "'"
        print(user.friends)
        session.commit()
    return redirect(f'/profile/{user_id}')


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route('/settings', methods=['GET', 'POST'])
def get_settings():
    form = SettingForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.id == current_user.id).first()
        if form.avatar.data:
            user.avatar_url = form.avatar.data
        if form.name.data:
            user.name = form.name.data
        if form.status.data:
            user.about = form.status.data
        if form.background.data:
            user.background = form.background.data
        user.theme = form.theme.data
        session.commit()
    return render_template('settings.html', title='Параметры', form=form, base=get_base())


@app.route('/profile/<user_id>')
def get_profile(user_id):
    form = ProfileForm()
    session = db_session.create_session()
    user = session.query(User).filter(User.id == user_id).first()
    form.user = user
    friend = '' if user.friends is None else user.friends
    if len(friend) > 0:
        friends = session.query(User).filter(User.id.in_(friend.strip("'").split(', ')))
        form.friends = friends
    else:
        form.friends = []
        form.error = 'Этот пользователь пока одинок. Напиши ему, может подружитесь.'
    return render_template('profile.html', title='Профиль', form=form, base=get_base())


@app.route('/profile')
def return_profile():
    return redirect(f'/profile/{current_user.id}')


@app.route('/news', methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        news = News()
        news.title = form.title.data
        news.content = form.content.data
        news.is_private = form.is_private.data
        current_user.news.append(news)
        session.merge(current_user)
        session.commit()
        return redirect('/')
    return render_template('news.html', title='Добавление новости',
                           form=form, base=get_base())


@app.route('/people/find/<userfind>', methods=['GET', 'POST'])
def user_find(userfind):
    form = UsersForm()
    if request.method == 'GET':
        session = db_session.create_session()
        print('Ok')
    if form.validate_on_submit():
        print('send')


@app.route('/news/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    if request.method == "GET":
        session = db_session.create_session()
        news = session.query(News).filter(News.id == id,
                                          News.user == current_user).first()
        if news:
            form.title.data = news.title
            form.content.data = news.content
            form.is_private.data = news.is_private
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        news = session.query(News).filter(News.id == id,
                                          News.user == current_user).first()
        if news:
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            session.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('news.html', title='Редактирование новости', form=form, base=get_base())


@app.route("/people", methods=["GET", "POST"])
def get_people():
    form = UsersForm()
    if form.validate_on_submit():
        print(form.find_string.data)
        redirect('/profile')
    session = db_session.create_session()
    users = session.query(User)
    return render_template("people.html", form=form, users=users, title='Люди', base=get_base())


@app.route('/news_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    session = db_session.create_session()
    news = session.query(News).filter(News.id == id,
                                      News.user == current_user).first()
    if news:
        session.delete(news)
        session.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form, base=get_base())


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if not check_password(form.password.data):
            if form.password.data != form.password_again.data:
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Пароли не совпадают")
        else:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message=check_password(form.password.data))
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        if session.query(User).filter(User.name == form.name.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form, base=get_base())


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/")
def index():
    session = db_session.create_session()
    if current_user.is_authenticated:
        news = session.query(News).filter(
            (News.user == current_user) | (News.is_private != True))
    else:
        news = session.query(News).filter(News.is_private != True)
    return render_template("index.html", news=news, title='Лента', base=get_base())


@app.route("/cookie_test")
def cookie_test():
    visits_count = int(request.cookies.get("visits_count", 0))
    if visits_count:
        res = make_response(f"Вы пришли на эту страницу {visits_count + 1} раз")
        res.set_cookie("visits_count", str(visits_count + 1),
                       max_age=60 * 60 * 24 * 365 * 2)
    else:
        res = make_response(
            "Вы пришли на эту страницу в первый раз за последние 2 года")
        res.set_cookie("visits_count", '1',
                       max_age=60 * 60 * 24 * 365 * 2)
    return res


@app.route('/session_test/')
def session_test():
    if 'visits_count' in session:
        session['visits_count'] = session.get('visits_count') + 1
        res = make_response(f"Вы пришли на эту страницу {session['visits_count']} раз")
    else:
        session.permanent = True
        session['visits_count'] = 1
        res = make_response(
            "Вы пришли на эту страницу в первый раз за последние 2 года")
    return res


def main():
    db_session.global_init("db/Memenews.sqlite")
    # app.register_blueprint(news_api.blueprint)
    api.add_resource(news_resources.NewsListResource, '/api/v2/news')
    api.add_resource(news_resources.NewsResource, '/api/v2/news/<int:news_id>')
    app.run()


if __name__ == '__main__':
    main()
