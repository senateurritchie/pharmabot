# -*-coding:utf-8 -*-
from flask import (Flask, flash,request, make_response as response, abort, redirect,url_for,render_template as render, session,escape,g,Blueprint)

from werkzeug.security  import check_password_hash,generate_password_hash

import pymongo
from bson.objectid import ObjectId
import functools
import datetime
import os
DATABASE_URL = os.environ["DATABASE_URL"]

bp = Blueprint('security', __name__, url_prefix='/security')

role_hierachy = {
	"role_admin":[
		"role_user",
		"role_operator_remove",
		"role_operator_insert",
		"role_survey",
		"role_quizz",
		"role_pharmacy"
	],
	"role_super_admin":["role_admin"]
}

client = pymongo.MongoClient(DATABASE_URL)
db = client.pharma_garde


def _is_granted(role):
	if g.user is None:
		return False

	table = set()

	def fill_role_hierachy(r):
		if r in role_hierachy:
			if type(role_hierachy[r]) == list:
				for i in role_hierachy[r]:
					table.add(fill_role_hierachy(i))
		return r

	for r in g.user['roles']:
		table.add(fill_role_hierachy(r))


	if type(role) == str:
		if role.strip().lower() not in table:
			return False

	elif type(role) == list:
		for el in role:
			if el.strip().lower() not in table:
				return False

	return True


def is_granted(role):
	def wrapped(view):
		@functools.wraps(view)
		def wrapped_view(**kwargs):

			if _is_granted(role) != True:
				return abort(403)

			return view(**kwargs)

		return wrapped_view
	return wrapped

def login_guard(view):
	@functools.wraps(view)
	def wrapped_view(**kwargs):
		if g.user is None:
			return redirect(url_for('security.login'))

		return view(**kwargs)

	return wrapped_view


@bp.before_app_request
def load_logged_in_user():

	
	user_id = session.get('user_id')

	if user_id is None:
		g.user = None
	else:
		g.user = db.admin.find_one({"_id":ObjectId(user_id)})


@bp.route("/register", methods=('GET','POST'))
def register():

	if g.user is not None:
		return redirect(url_for("index"))

	if request.method == 'POST':
		email = request.form['email']
		username = request.form['username']
		password = request.form['password']
		cpassword = request.form['cpassword']
		error = None
		

		if not email:
			error = 'Email is required.'
		elif not username:
			error = 'Username is required.'
		elif not password or not cpassword:
			error = 'Password is required.'
		elif password != cpassword:
			error = 'Password and his confirmation must match.'
		elif db.admin.find_one({"email":email},{"email":1,"_id":0}) is not None:
			error = 'Email {} is already registered.'.format(email)

		if error is None:
			db.admin.insert_one({
				"email":email,
				"username":username,
				"password":generate_password_hash(password),
				"roles":["role_user"],
				"create_at":datetime.datetime.utcnow()
			})

			return redirect(url_for('security.login'))

		flash(error)

	return render('security/register.html.jinja2')


@bp.route("/login", methods=('GET','POST'))
def login():

	if g.user is not None:
		return redirect(url_for("admin.index"))

	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		error = None

		user = db.admin.find_one({"email":username})


		if user is None:
			error = 'Incorrect username.'
		elif not check_password_hash(user['password'], password):
			error = 'Incorrect password.'

		if error is None:
			session.clear()
			session['user_id'] = str(user['_id'])
			return redirect(url_for('admin.index'))

		flash(error)

	return render('security/login.html.jinja2')

@bp.route('/logout')
@login_guard
def logout():
	session.clear()
	return redirect(url_for('security.login'))