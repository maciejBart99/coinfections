import logging
import os
import uuid
from collections import defaultdict

import jwt
from flask import Flask, render_template, request, make_response, send_from_directory
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, SubmitField, FileField, MultipleFileField
from wtforms.validators import DataRequired

from service import get_all_orders, create_order, get_by_id
from order import DB

SECRET = os.environ.get('COINFECTIONS_SECRET')

app = Flask("Coinfections")
app.config['SECRET_KEY'] = SECRET
app.logger.setLevel(logging.INFO)
Bootstrap(app)


class OrdersFrom(FlaskForm):
    name = StringField('Sample name', validators=[DataRequired()])
    file_1 = FileField('Read file', validators=[FileRequired(), FileAllowed(['faq', 'fastaq', 'gz'], 'Only fastaq')])
    file_2 = FileField('Paired file', validators=[FileRequired(), FileAllowed(['faq', 'fastaq', 'gz'], 'Only fastaq')])
    positions = StringField('Positions (comma separated)', validators=[DataRequired()])
    submit = SubmitField('Submit')


class OrdersMultiFrom(FlaskForm):
    files = FileField('Files, paired files should have names {name}_R1.fastaq.gz and {name}_R2.fastaq.gz.'
                              ' {name} will be taken as a sample name', render_kw={'multiple': True})
    positions = StringField('Positions (comma separated)', validators=[DataRequired()])
    submit = SubmitField('Submit')


def get_user_id(token: str) -> str:
    d_jwt = jwt.decode(token, SECRET, algorithms=["HS256"])
    if d_jwt is None:
        return ''
    else:
        return d_jwt['id']


def make_jwt() -> str:
    user_id = str(uuid.uuid4())
    s_jwt = jwt.encode({'id': user_id}, SECRET, algorithm="HS256")
    return s_jwt


@app.route("/", methods=['GET', 'POST'])
def index():
    session = DB()
    form = OrdersFrom()

    if not os.path.exists('uploads'):
        os.mkdir('uploads')

    if 'jwt' in request.cookies:
        user_id = get_user_id(request.cookies.get('jwt'))

        if form.validate_on_submit():
            file_1_path = f'uploads/{uuid.uuid4()}-{form.file_1.data.filename}'
            file_2_path = f'uploads/{uuid.uuid4()}-{form.file_2.data.filename}'
            create_order(form.name.data, file_1_path, file_2_path, user_id, form.positions.data, session)
            form.file_1.data.save(file_1_path)
            form.file_2.data.save(file_2_path)
            form = OrdersFrom()

        orders = get_all_orders(user_id, session)
        return render_template("index.html", orders=orders, form=form)
    elif request.method == 'GET':
        resp = make_response(render_template('index.html', orders=[], form=form))
        resp.set_cookie('jwt', make_jwt())
        return resp
    else:
        return 'FATAL ERROR', 401


@app.route("/multi", methods=['GET', 'POST'])
def multi():
    session = DB()
    form = OrdersMultiFrom()

    if not os.path.exists('uploads'):
        os.mkdir('uploads')

    if 'jwt' in request.cookies:
        user_id = get_user_id(request.cookies.get('jwt'))
        if form.validate_on_submit():
            paired = defaultdict(lambda: [])
            files = request.files.getlist(form.files.name)
            for f in files:
                file_without_ex = f.filename.split('.')[0]
                name = file_without_ex.rsplit('_', 2)[0]
                print(file_without_ex.rsplit('_', 2))
                file_path = f'uploads/{uuid.uuid4()}-{f.filename}'
                f.save(file_path)
                if file_without_ex.endswith('_R1'):
                    paired[name].append(file_path)
                elif file_without_ex.endswith('_R2'):
                    paired[name].append(file_path)
                else:
                    return 'Invalid upload', 400
            for key in paired.keys():
                if len(paired[key]) == 2:
                    create_order(key, paired[key][0], paired[key][1], user_id, form.positions.data, session)
                else:
                    return 'Invalid upload', 400
            form = OrdersMultiFrom()

        orders = get_all_orders(user_id, session)
        return render_template("index.html", orders=orders, form=form)
    elif request.method == 'GET':
        resp = make_response(render_template('index.html', orders=[], form=form))
        resp.set_cookie('jwt', make_jwt())
        return resp
    else:
        return 'FATAL ERROR', 401


@app.route("/files/<order>", methods=['GET'])
def file_serve(order: int):
    session = DB()

    if 'jwt' in request.cookies:
        user_id = get_user_id(request.cookies.get('jwt'))
        order = get_by_id(order, session)

        if user_id != order.user_id or order.state != 'READY':
            return 'FATAL ERROR', 400

        return send_from_directory('results', order.result_path.split('/')[-1], as_attachment=True)
    else:
        return 'FATAL ERROR', 401


if __name__ == '__main__':
    if not os.path.exists('results'):
        os.mkdir('results')
    app.run(port=8080)

