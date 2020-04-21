# -*-coding:utf-8 -*-
from flask import (Flask, flash,request, make_response as response, abort, redirect,url_for,render_template as render, session,escape,g,Blueprint)

from werkzeug.security  import check_password_hash,generate_password_hash

import pymongo
from bson.objectid import ObjectId
import functools

from ..modules.security import login_guard,is_granted
from ..OfficineUpdater import OfficineUpdater


import json
import datetime
from slugify import slugify
from bson import json_util
import os
DATABASE_URL = os.environ["DATABASE_URL"]

bp = Blueprint('admin', __name__, url_prefix='/admin')

client = pymongo.MongoClient(DATABASE_URL)
db = client.pharma_garde

@bp.route("/", methods=('GET',))
@is_granted("role_admin")
@login_guard
def index():
	"""
	page d'accueil de la zone d'administration
	"""

	data_users = db.user.aggregate([
		{
			"$lookup":{
				"from":"consultation",
				"let":{"user_id":"$_id"},
				"pipeline":[
					{ 
						"$match":{
							"$expr":{
	                         	"$and":[
	                         		{"$eq": [ "$user_id",  "$$user_id" ]},
	                         	]
	                    	}
	                 	}
	              	},
	              	{
                 		"$group":{
                 			"_id":None,
                 			"total":{"$sum":1}
                 		}
	                },
	                {"$project":{"_id":0}}
				],
				"as":"tickets"
			}
		},
		{"$addFields":{"tickets":{"$arrayElemAt":["$tickets",0]}}},
		{"$addFields":{"tickets":"$tickets.total"}},
		{"$sort":{"last_presence":-1}},
		{"$limit":10},
	])

	data_users = [i for i in data_users]

	stats_user = db.user.count_documents({})
	stats_ticket = db.consultation.count_documents({})
	stats_denunc = db.denunciation.count_documents({"state":"submited"})
	stats_op = db.crisis_operator.count_documents({})

	return render('admin/index.html',data_users=data_users,stats_user=stats_user,stats_ticket=stats_ticket,stats_denunc=stats_denunc,stats_op=stats_op)


@bp.route("/dashboard/denunciation", methods=('GET',))
@is_granted("role_super_admin")
@login_guard
def dashboard_denunciation():
	"""
	tableau de bord des denonctions
	"""
	return render('admin/index.html')

@bp.route("/users", methods=('GET',))
@is_granted("role_super_admin")
@login_guard
def users():
	"""
	tableau de bord des denonctions
	"""
	
	data = db.user.aggregate([
		{
			"$lookup":{
				"from":"consultation",
				"let":{"user_id":"$_id"},
				"pipeline":[
					{ 
						"$match":{
							"$expr":{
	                         	"$and":[
	                         		{"$eq": [ "$user_id",  "$$user_id" ]},
	                         	]
	                    	}
	                 	}
	              	},
	              	{
                 		"$group":{
                 			"_id":{"state":"$state"},
                 			"total":{"$sum":1}
                 		}
	                },
	                {"$addFields":{"state":"$_id.state"}},

	                {"$project":{"_id":0}}
				],
				"as":"tickets"
			}
		},
		# {"$addFields":{"tickets":{"$arrayElemAt":["$tickets",0]}}},
		# {"$addFields":{"tickets":"$tickets.total"}},
		{"$sort":{"_id":-1}},
		{"$limit":50}
	])

	data = [i for i in data]

	# for el in data:
	# 	el["user"] = el["user"][0]

	return render('admin/users-index.html', data=data)



@bp.route("/garde-periods", methods=('GET',))
@is_granted("role_pharmacy")
@login_guard
def garde_periods():
	"""
	tableau de bord des denonctions
	"""
	data = db.garde_period.aggregate([
		
		{"$sort":{"_id":-1}},
		{"$limit":50},
		# {
		# 	"$lookup":{
		# 		"from":"admin",
		# 		"localField":"create_by",
		# 		"foreignField":"_id",
		# 		"as":"author"
		# 	}
		# },
		# {"$addFields":{"author":{"$arrayElemAt":["$author",0]}}},

		{
			"$lookup":{
				"from":"garde_period_view",
				"let":{"_id":"$garde_period_id"},
				"pipeline":[
					{ 
						"$match":{
							"$expr":{
	                         	"$eq": [ "$garde_period_id",  "$$garde_period_id" ]
	                    	}
	                 	}
	              	},
	              	{
                 		"$group":{
                 			"_id":None,
                 			"total":{"$sum":1}
                 		}
	                },
	                {"$project":{"_id":0}}
				],
				"as":"views"
			}
		},
		{"$addFields":{"views":{"$arrayElemAt":["$views",0]}}}
	])

	data = [i for i in data]

	return render('admin/garde-periods-index.html.jinja2', data=data)


@bp.route("/garde-periods/upload", methods=('POST',))
@is_granted("role_pharmacy")
@login_guard
def garde_periods_upload():
	"""
	pour charger une nouvelle periode de garde
	avec un fichier .txt
	"""
	file = request.files["file"]
	updater = OfficineUpdater()

	try:
		logs = updater.saveGardeList2(file.read().decode(), request.form.get("save") == "on")

		for log in logs:
			flash(log,'info')

	except Exception as e:
		flash(str(e),'danger')
		

	return redirect(url_for("admin.garde_periods"))



@bp.route("/garde-periods/<garde_period_id>/pharmacies", methods=('GET',))
@is_granted("role_pharmacy")
@login_guard
def get_pharmacies_garde_period(garde_period_id):
	"""
	tableau de bord des denonctions
	"""

	result = {"status":False}
	garde_period = db.garde_period.find_one({"_id":ObjectId(garde_period_id)})

	if not garde_period:
		result["logs"] = "cette periode de garde n'existe pas"
	else:
		result["payload"] = {"period":garde_period}

		stages = [
			{"$match":{
				"garde_period_id":garde_period["_id"]
			}},
			{"$lookup":{
				"from":"locality",
				"localField":"locality_slug",
				"foreignField":"slug",
				"as":"locality"
			}},
			{"$sort":{"zone":1,"locality_slug":1,}},
			{"$addFields":{"locality":{"$arrayElemAt":["$locality",0]}}},

		]

		pharmacies = db.garde.aggregate(stages)
		pharmacies = [i for i in pharmacies]
		result["payload"]["html"] = render('admin/garde-period-pharmacies-tpl.html.jinja2', pharmacies=pharmacies,period=garde_period)

	r = response(json.dumps(result, default=json_util.default))
	r.headers["content-type"] = "application/json"

	return r,200


@bp.route("/garde-periods/<garde_period_id>/activation", methods=('POST',))
@is_granted("role_pharmacy")
@login_guard
def activate_garde_period(garde_period_id):
	"""
	pour activer et desactiver une periode de garde
	"""

	result = {"status":False}
	garde_period = db.garde_period.find_one({"_id":ObjectId(garde_period_id)})

	if not garde_period:
		result["logs"] = "cette periode de garde n'existe pas"
	else:
		result['status'] = True

		state = int(request.form.get("state"))



		if state == 1:
			db.garde_period.update_many({
				"is_active":True
			},{
				"$set":{
					"is_active":False
				}
			})

			db.garde_period.update_one({
				"_id":garde_period["_id"]
			},{
				"$set":{
					"is_active":True
				}
			})

		elif state == 0:

			db.garde_period.update_many({
				"_id":garde_period["_id"]
			},{
				"$set":{
					"is_active":False
				}
			})

	r = response(json.dumps(result, default=json_util.default))
	r.headers["content-type"] = "application/json"

	return r,200




@bp.route("/quizz", methods=('GET','POST'))
@is_granted("role_quizz")
@login_guard
def quizz():
	"""
	onglet de gestion des quizz 
	"""
	data = db.quizz.aggregate([

		{"$sort":{"_id":-1}},
		{"$limit":20},
		{
			"$lookup":{
				"from":"admin",
				"localField":"create_by",
				"foreignField":"_id",
				"as":"author"
			}
		},
		{"$addFields":{"author":{"$arrayElemAt":["$author",0]}}},
	])

	data = [i for i in data]

	return render('admin/quizz-index.html.jinja2', data=data)

@bp.route("/quizz/<quizz_id>", methods=('GET',))
@is_granted("role_quizz")
@login_guard
def get_quizz(quizz_id):
	"""
	on recherche un quizz
	"""
	survey = db.quizz.find_one({"_id":ObjectId(quizz_id)})

	if survey is None:
		return abort(404)

	del survey["users"]
	del survey["create_by"]
	del survey["create_at"]

	r = response(json.dumps(survey, default=json_util.default))
	r.headers["content-type"] = "application/json"

	return r,200

@bp.route("/quizz/<quizz_id>/questions/<question_id>/save", methods=('POST',))
@is_granted("role_quizz")
@login_guard
def quizz_question_save(quizz_id,question_id):
	"""
	on met a jour un question d'un quizz
	"""
	quizz_id = ObjectId(quizz_id)
	question_id = ObjectId(question_id)
	payload = request.form["payload"]
	result = {"status":False}

	if len(payload.strip()):
		survey = db.quizz.find_one({"_id":quizz_id})

		if survey:
			for question in survey["questions"]:
				if question["_id"] == question_id:
					question["payload"] = payload
					result["_id"] = str(question["_id"])
					break

			db.quizz.update_one({
				"_id":quizz_id
			},{
				"$set":{
					"questions":survey["questions"]
				}
			})

			result["status"] = True
	else:
		result["logs"] = "veuiller saisir la question svp"

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"

	return r,200


@bp.route("/quizz/<quizz_id>/questions/<question_id>/delete", methods=('POST',))
@is_granted("role_quizz")
@login_guard
def quizz_question_delete(quizz_id,question_id):
	"""
	suppresion d'une question dans un quizz
	"""

	quizz_id = ObjectId(quizz_id)
	question_id = ObjectId(question_id)
	result = {"status":False}

	survey = db.quizz.find_one({"_id":quizz_id})

	if survey:
		for i,question in enumerate(survey["questions"]):
			if question["_id"] == question_id:
				answered = [oo for oo in question['choices'] if oo["answers"]]
				if len(answered) > 0:
					result["logs"] = "Impossible de supprimer cette question, des utilisateurs y ont déja repondu"
					break

				del survey["questions"][i]

				db.quizz.update_one({
					"_id":quizz_id
				},{
					"$set":{
						"questions":survey["questions"]
					}
				})

				result["status"] = True

				break

		

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"
	return r,200


@bp.route("/quizz/<quizz_id>/questions/add", methods=('POST',))
@is_granted("role_quizz")
@login_guard
def quizz_question_add(quizz_id):
	"""
	pour ajouter une question à un quizz
	"""
	
	quizz_id = ObjectId(quizz_id)
	result = {"status":False}

	survey = db.quizz.find_one({"_id":quizz_id})

	if survey:
		result["choice_ids"] = []

		questions = []
		has_error = False


		for i,v in enumerate(request.form.getlist('question')):
			if not v.strip():
				result["logs"] = "veuiller saisir la question svp"
				has_error = True
				continue


			choices_is_true = request.form.getlist('response_check[{}][1]'.format(i+1))
			autoresponders = request.form.getlist('autoresponder[{}]'.format(i+1))

			question = {
				"_id":ObjectId(),
				"type":"text",
				"payload":v,
				"choices":[]
			}

			result["_id"] = str(question["_id"])

			for ii,vv in enumerate(request.form.getlist('response[{}]'.format(i+1))):
				if not vv.strip():
					result["logs"] = "veuiller saisir la reponse {} svp".format(ii+1)
					has_error = True
					break  

				choice_id = ObjectId()

				choice_is_true = choices_is_true[ii] == "on"
				autoresponder = autoresponders[ii]

				question["choices"].append({
					"_id":choice_id,
					"is_true":choice_is_true,
					"autoresponder":autoresponder,
					"type":"text",
					"payload":vv,
					"answers":0
				})
				result["choice_ids"].append(str(choice_id))

			if len(question["choices"]) and has_error == False:
				survey["questions"].append(question)

				db.quizz.update_one({
					"_id":quizz_id
				},{
					"$set":{
						"questions":survey["questions"]
					}
				})

				result["status"] = True
				break
		

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"
	return r,200


@bp.route("/quizz/<quizz_id>/questions/<question_id>/responses/<response_id>/save", methods=('POST',))
@is_granted("role_quizz")
@login_guard
def quizz_response_save(quizz_id,question_id,response_id):
	"""
	on met a jour la reponse d'une question d'un quizz
	"""

	quizz_id = ObjectId(quizz_id)
	question_id = ObjectId(question_id)
	response_id = ObjectId(response_id)
	payload = request.form["payload"]
	is_true = request.form["is_true"]
	auto_responder = request.form["auto_responder"]
	result = {"status":False}

	if len(payload.strip()):
		survey = db.quizz.find_one({"_id":quizz_id})

		if survey is None:
			return abort(404)

		isexists = False
		for question in survey["questions"]:
			if question["_id"] == question_id:
				for choice in question["choices"]:
					if choice["_id"] == response_id:
						choice["payload"] = payload
						choice["is_true"] = is_true == "on"
						choice["autoresponder"] = auto_responder.strip()
						isexists = True
						result["_id"] = str(choice["_id"])
						break
				break

		if isexists:
			db.quizz.update_one({
				"_id":quizz_id
			},{
				"$set":{
					"questions":survey["questions"]
				}
			})

			result["status"] = True
	else:
		result["logs"] = "veuiller saisir la reponse svp"


	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"

	return r,200


@bp.route("/quizz/<quizz_id>/questions/<question_id>/responses/<response_id>/delete", methods=('POST',))
@is_granted("role_quizz")
@login_guard
def quizz_response_delete(quizz_id,question_id,response_id):
	"""
	on supprime une reponse a une question d'un quizz
	"""

	quizz_id = ObjectId(quizz_id)
	question_id = ObjectId(question_id)
	response_id = ObjectId(response_id)
	result = {"status":False}

	survey = db.quizz.find_one({"_id":quizz_id})

	if survey is None:
		return abort(404)

	isexists = False
	for question in survey["questions"]:
		if question["_id"] == question_id:
			if len(question["choices"]) == 2:
				result["logs"] = "Une question doit avoir mininum 2 propositions de reponse"
				break
			for i,choice in enumerate(question["choices"]):
				if choice["_id"] == response_id:
					del question["choices"][i]
					isexists = True
					break
			break

	if isexists:
		db.quizz.update_one({
			"_id":quizz_id
		},{
			"$set":{
				"questions":survey["questions"]
			}
		})
		result["status"] = True

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"

	return r,200


@bp.route("/quizz/<quizz_id>/questions/<question_id>/responses/add", methods=('POST',))
@is_granted("role_quizz")
@login_guard
def quizz_response_add(quizz_id,question_id):
	"""
	on ajoute une reponse à une question d'un quizz
	"""
	quizz_id = ObjectId(quizz_id)
	question_id = ObjectId(question_id)
	payload = request.form["payload"]
	auto_responder = request.form["auto_responder"]
	is_true = request.form["is_true"]
	result = {"status":False}

	if len(payload.strip()):
		survey = db.quizz.find_one({"_id":quizz_id})

		if survey is None:
			return abort(404)

		isexists = False
		for question in survey["questions"]:
			if question["_id"] == question_id:
				_id = ObjectId()
				question["choices"].append({
					"_id":_id,
					"type":"text",
					"payload":payload,
					"is_true":is_true == "on",
					"autoresponder":auto_responder,
					"answers":0
				})
				result["_id"] = str(_id)
				isexists = True
				break

		if isexists:
			db.quizz.update_one({
				"_id":quizz_id
			},{
				"$set":{
					"questions":survey["questions"]
				}
			})
			result["status"] = True

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"

	return r,200


@bp.route("/quizz/<quizz_id>/save", methods=('POST',))
@bp.route("/quizz/save", methods=('POST',))
@is_granted("role_quizz")
@login_guard
def quizz_save(quizz_id=None):
	"""
	ajouter un quizz
	"""
	
	quizz_id = quizz_id if quizz_id is not None else request.form.get("quizz_id",None)
	title = request.form.get("title","").strip()
	good_resp_msg = request.form.get("good_resp_msg","").strip()
	bad_resp_msg = request.form.get("bad_resp_msg","").strip()
	is_active = request.form.get("is_active",False)
	is_active = True if is_active == "on" else is_active
	is_stick = request.form.get("is_stick",False)
	is_stick = True if is_stick == "on" else is_stick
	slug = slugify(title)
	is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'


	if len(title) == 0:
		if is_xhr:
			return "",200

		flash("attention, veuiller saisir le titre du sondage",'danger')
		return redirect(url_for("admin.quizz"))

	if quizz_id is not None:
		survey = db.quizz.find_one({"_id":ObjectId(quizz_id)})

		if survey is None:
			return abort(404)

		db.quizz.update_one({
				"_id":survey["_id"]
			},
			{
				"$set":{
					"title":title,
					"good_resp_txt":good_resp_msg,
					"bad_resp_txt":bad_resp_msg,
					"slug":slug,
					"is_active":is_active,
					"is_stick":is_stick,
				}
			}
		)
	else:
		survey = db.quizz.find_one({"slug":slugify(title)})

		if survey is not None:
			if is_xhr:
				return "",200

			flash("attention, ce quizz existe déla",'danger')
			return redirect(url_for("admin.quizz"))

		else:

			questions = []

			for i,v in enumerate(request.form.getlist('question')):
				question = {
					"_id":ObjectId(),
					"type":"text",
					"payload":v,
					"choices":[]
				}

				for ii,vv in enumerate(request.form.getlist('response[{}]'.format(i+1))):
					choice_is_true = request.form.get('response_check[{}][{}]'.format(i+1,ii+1)) == "on"
					autoresponder = request.form.get('autoresponder[{}]'.format(ii+1)).strip()

					question["choices"].append({
						"_id":ObjectId(),
						"is_true":choice_is_true,
						"autoresponder":autoresponder,
						"type":"text",
						"payload":vv,
						"answers":0
					})

				questions.append(question)

			_id = db.quizz.insert_one({
				"create_by":g.user["_id"],
				"title":title,
				"good_resp_txt":good_resp_msg,
				"bad_resp_txt":bad_resp_msg,
				"slug":slug,
				"welcome_text":None,
				"end_text":None,
				"is_active":is_active,
				"is_stick":is_stick,
				"is_closed":False,
				"create_at":datetime.datetime.utcnow(),
				"users":[],
				"questions":questions,
			}).inserted_id

	if is_xhr:
		return "",200

	flash("l'opération à bien été effectuée avec succes",'info')

	return redirect(url_for("admin.quizz"))


@bp.route("/quizz/delete", methods=('POST',))
@is_granted("role_admin")
@login_guard
def quizz_delete():
	"""
	supprimer un quizz
	"""
	quizz_id = ObjectId(request.form["quizz_id"])
	survey = db.quizz.find_one({"_id":quizz_id})

	if survey is None:
		return abort(404)

	if len(survey["users"]) > 0:
		flash("attention ce sondage ne peut pas être supprimé car il a {} participants a son actif".format(len(survey['users']) ),'danger')
	else:
		db.quizz.delete_one({"_id":quizz_id})
		flash("le sondage à bien été supprimé avec succes",'info')

	return redirect(url_for("admin.quizz"))




#######################################################""

@bp.route("/surveys", methods=('GET','POST'))
@is_granted("role_survey")
@login_guard
def surveys():
	"""
	onglet de gestion des sondages 
	"""
	
	data = db.survey.aggregate([
		{"$sort":{"_id":-1}},
		{"$limit":20},
		{
			"$lookup":{
				"from":"admin",
				"localField":"create_by",
				"foreignField":"_id",
				"as":"author"
			}
		},
		{"$addFields":{"author":{"$arrayElemAt":["$author",0]}}},
	])

	data = [i for i in data]

	return render('admin/survey-index.html', data=data)


@bp.route("/surveys/<survey_id>", methods=('GET',))
@is_granted("role_survey")
@login_guard
def get_survey(survey_id):
	"""
	on recherche un ondage
	"""
	survey = db.survey.find_one({"_id":ObjectId(survey_id)})

	if survey is None:
		return abort(404)

	del survey["users"]
	del survey["create_by"]
	del survey["create_at"]

	r = response(json.dumps(survey, default=json_util.default))
	r.headers["content-type"] = "application/json"

	return r,200


@bp.route("/surveys/<survey_id>/questions/<question_id>/save", methods=('POST',))
@is_granted("role_survey")
@login_guard
def survey_question_save(survey_id,question_id):
	"""
	on met a jour un question d'un sondage
	"""

	

	survey_id = ObjectId(survey_id)
	question_id = ObjectId(question_id)
	payload = request.form["payload"]
	result = {"status":False}

	if len(payload.strip()):
		survey = db.survey.find_one({"_id":survey_id})

		if survey:
			for question in survey["questions"]:
				if question["_id"] == question_id:
					question["payload"] = payload
					result["_id"] = str(question["_id"])
					break

			db.survey.update_one({
				"_id":survey_id
			},{
				"$set":{
					"questions":survey["questions"]
				}
			})

			result["status"] = True
	else:
		result["logs"] = "veuiller saisir la question svp"

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"

	return r,200

@bp.route("/surveys/<survey_id>/questions/<question_id>/delete", methods=('POST',))
@is_granted("role_survey")
@login_guard
def survey_question_delete(survey_id,question_id):
	"""
	suppresion d'une question dans un sondage
	"""
	

	survey_id = ObjectId(survey_id)
	question_id = ObjectId(question_id)
	result = {"status":False}

	survey = db.survey.find_one({"_id":survey_id})

	if survey:
		for i,question in enumerate(survey["questions"]):
			if question["_id"] == question_id:
				answered = [oo for oo in question['choices'] if oo["answers"]]
				if len(answered) > 0:
					result["logs"] = "Impossible de supprimer cette question, des utilisateurs y ont déja repondu"
					break

				del survey["questions"][i]

				db.survey.update_one({
					"_id":survey_id
				},{
					"$set":{
						"questions":survey["questions"]
					}
				})

				result["status"] = True

				break

		

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"
	return r,200


@bp.route("/surveys/<survey_id>/questions/add", methods=('POST',))
@is_granted("role_survey")
@login_guard
def survey_question_add(survey_id):
	"""
	pour ajouter une question à un sondage
	"""
	

	survey_id = ObjectId(survey_id)
	result = {"status":False}

	survey = db.survey.find_one({"_id":survey_id})

	if survey:
		result["choice_ids"] = []

		questions = []
		has_error = False
		for i,v in enumerate(request.form.getlist('question')):
			if not v.strip():
				result["logs"] = "veuiller saisir la question svp"
				has_error = True
				continue

			question = {
				"_id":ObjectId(),
				"type":"text",
				"payload":v,
				"is_required":True,
				"choices":[]
			}

			result["_id"] = str(question["_id"])

			for ii,vv in enumerate(request.form.getlist('response[{}]'.format(i+1))):
				if not vv.strip():
					result["logs"] = "veuiller saisir la reponse {} svp".format(ii+1)
					has_error = True
					break

				choice_id = ObjectId()
				question["choices"].append({
					"_id":choice_id,
					"type":"text",
					"payload":vv,
					"answers":0
				})
				result["choice_ids"].append(str(choice_id))

			if len(question["choices"]) and has_error == False:
				survey["questions"].append(question)

				db.survey.update_one({
					"_id":survey_id
				},{
					"$set":{
						"questions":survey["questions"]
					}
				})

				result["status"] = True
				break
		

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"
	return r,200


@bp.route("/surveys/<survey_id>/questions/<question_id>/responses/<response_id>/save", methods=('POST',))
@is_granted("role_survey")
@login_guard
def survey_response_save(survey_id,question_id,response_id):
	"""
	on met a jour la reponse d'une question d'un sondage
	"""

	

	survey_id = ObjectId(survey_id)
	question_id = ObjectId(question_id)
	response_id = ObjectId(response_id)
	payload = request.form["payload"]
	result = {"status":False}

	if len(payload.strip()):
		survey = db.survey.find_one({"_id":survey_id})

		if survey is None:
			return abort(404)

		isexists = False
		for question in survey["questions"]:
			if question["_id"] == question_id:
				for choice in question["choices"]:
					if choice["_id"] == response_id:
						choice["payload"] = payload
						isexists = True
						result["_id"] = str(choice["_id"])
						break
				break

		if isexists:
			db.survey.update_one({
				"_id":survey_id
			},{
				"$set":{
					"questions":survey["questions"]
				}
			})

			result["status"] = True
	else:
		result["logs"] = "veuiller saisir la reponse svp"


	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"

	return r,200


@bp.route("/surveys/<survey_id>/questions/<question_id>/responses/<response_id>/delete", methods=('POST',))
@is_granted("role_survey")
@login_guard
def survey_response_delete(survey_id,question_id,response_id):
	"""
	on supprime une reponse a une question d'un sondage
	"""

	

	survey_id = ObjectId(survey_id)
	question_id = ObjectId(question_id)
	response_id = ObjectId(response_id)
	result = {"status":False}

	survey = db.survey.find_one({"_id":survey_id})

	if survey is None:
		return abort(404)

	isexists = False
	for question in survey["questions"]:
		if question["_id"] == question_id:
			if len(question["choices"]):
				result["logs"] = "Une question doit avoir mininum 2 propositions de reponse"
				break
			for i,choice in enumerate(question["choices"]):
				if choice["_id"] == response_id:
					del question["choices"][i]
					isexists = True
					break
			break

	if isexists:
		db.survey.update_one({
			"_id":survey_id
		},{
			"$set":{
				"questions":survey["questions"]
			}
		})
		result["status"] = True

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"

	return r,200


@bp.route("/surveys/<survey_id>/questions/<question_id>/responses/add", methods=('POST',))
@is_granted("role_survey")
@login_guard
def survey_response_add(survey_id,question_id):
	"""
	on ajoute une reponse à une question d'un sondage
	"""

	

	survey_id = ObjectId(survey_id)
	question_id = ObjectId(question_id)
	payload = request.form["payload"]
	result = {"status":False}

	if len(payload.strip()):
		survey = db.survey.find_one({"_id":survey_id})

		if survey is None:
			return abort(404)

		isexists = False
		for question in survey["questions"]:
			if question["_id"] == question_id:
				_id = ObjectId()
				question["choices"].append({
					"_id":_id,
					"type":"text",
					"payload":payload,
					"answers":0
				})
				result["_id"] = str(_id)
				isexists = True
				break

		if isexists:
			db.survey.update_one({
				"_id":survey_id
			},{
				"$set":{
					"questions":survey["questions"]
				}
			})
			result["status"] = True

	r = response(json.dumps(result))
	r.headers["content-type"] = "application/json"

	return r,200





@bp.route("/survey/<survey_id>/save", methods=('POST',))
@bp.route("/survey/save", methods=('POST',))
@is_granted("role_survey")
@login_guard
def survey_save(survey_id=None):
	"""
	ajouter un sujet de crise
	"""
	
	survey_id = survey_id if survey_id is not None else request.form.get("survey_id",None)
	title = request.form.get("title","").strip()
	is_active = request.form.get("is_active",False)
	is_active = True if is_active == "on" else is_active
	is_stick = request.form.get("is_stick",False)
	is_stick = True if is_stick == "on" else is_stick
	slug = slugify(title)
	is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'


	if len(title) == 0:
		if is_xhr:
			return "",200

		flash("attention, veuiller saisir le titre du sondage",'danger')
		return redirect(url_for("admin.surveys"))

	if survey_id is not None:
		survey = db.survey.find_one({"_id":ObjectId(survey_id)})

		if survey is None:
			return abort(404)

		db.survey.update_one({
				"_id":survey["_id"]
			},
			{
				"$set":{
					"title":title,
					"slug":slug,
					"is_active":is_active,
					"is_stick":is_stick,
				}
			}
		)
	else:
		survey = db.survey.find_one({"slug":slugify(title)})

		if survey is not None:
			if is_xhr:
				return "",200

			flash("attention, ce sondage existe déla",'danger')
			return redirect(url_for("admin.surveys"))

		else:

			questions = []

			for i,v in enumerate(request.form.getlist('question')):
				question = {
					"_id":ObjectId(),
					"type":"text",
					"payload":v,
					"is_required":True,
					"choices":[]
				}

				for ii,vv in enumerate(request.form.getlist('response[{}]'.format(i+1))):
					question["choices"].append({
						"_id":ObjectId(),
						"type":"text",
						"payload":vv,
						"answers":0
					})

				questions.append(question)

			_id = db.survey.insert_one({
				"create_by":g.user["_id"],
				"title":title,
				"slug":slug,
				"welcome_text":None,
				"end_text":None,
				"is_active":is_active,
				"is_stick":is_stick,
				"is_closed":False,
				"create_at":datetime.datetime.utcnow(),
				"users":[],
				"questions":questions,
			}).inserted_id

	if is_xhr:
		return "",200

	flash("l'opération à bien été effectuée avec succes",'info')

	return redirect(url_for("admin.surveys"))


@bp.route("/survey/delete", methods=('POST',))
@is_granted("role_admin")
@login_guard
def survey_delete():
	"""
	supprimer un sondage
	"""
	survey_id = ObjectId(request.form["survey_id"])

	
	survey = db.survey.find_one({"_id":survey_id})

	if survey is None:
		return abort(404)

	if len(survey["users"]) > 0:
		flash("attention ce sondage ne peut pas être supprimé car il a {} participants a son actif".format(len(survey['users']) ),'danger')
	else:
		db.survey.delete_one({"_id":survey_id})
		flash("le sondage à bien été supprimé avec succes",'info')

	return redirect(url_for("admin.surveys"))






@bp.route("/dashboard/crisis", methods=('GET',))
@is_granted("role_super_admin")
@login_guard
def dashboard_crisis():
	"""
	tableau de bord des gestions de crises
	"""
	return render('admin/index.html')


@bp.route("/crisis", methods=('GET','POST'))
@is_granted("role_super_admin")
@login_guard
def crisis():
	"""
	onglet de gestion de crises
	"""

	
	data = db.crisis.aggregate([
		{
			"$lookup":{
				"from":"consultation",
				"let":{"crisis_id":"$_id"},
				"pipeline":[
					{ 
						"$match":{
							"$expr":{
	                         	"$and":[
	                         		{"$eq": [ "$crisis_id",  "$$crisis_id" ]},
	                         	]
	                    	}
	                 	}
	              	},
	              	{
                 		"$group":{
                 			"_id":{"state":"$state"},
                 			"total":{"$sum":1}
                 		}
	                },
	                {"$addFields":{"state":"$_id.state"}},

	                {"$project":{"_id":0}}
				],
				"as":"tickets"
			}
		},
		{"$sort":{"_id":-1}},
		{"$limit":20},
		# {"$addFields":{"tickets":{"$arrayElemAt":["$tickets",0]}}},
		# {"$addFields":{"tickets":"$tickets.total"}},
	])

	data = [i for i in data]


	# for el in data:
	# 	el["user"] = el["user"][0]
	# 	
	return render('admin/crisis-index.html', data=data)




@bp.route("/crisis/save", methods=('POST',))
@is_granted("role_super_admin")
@login_guard
def crisis_save():
	"""
	ajouter un sujet de crise
	"""
	

	crisis_id = request.form.get("crisis_id",None)
	name = request.form.get("name","").strip()
	is_active = request.form.get("is_active",False)
	is_active = True if is_active == "on" else is_active

	is_stick = request.form.get("is_stick",False)
	is_stick = True if is_stick == "on" else is_stick

	slug = slugify(name)

	if len(name) == 0:
		flash("attention, veuiller saisir le titre à inserer",'danger')
		return redirect(url_for("admin.crisis"))

	if crisis_id is not None:
		crisis = db.crisis.find_one({"_id":ObjectId(crisis_id)})

		if crisis is None:
			return abort(404)

		db.crisis.update_one({
				"_id":crisis["_id"]
			},
			{
				"$set":{
					"name":name,
					"slug":slug,
					"is_active":is_active,
					"is_stick":is_stick,
				}
			}
		)
	else:
		crisis = db.crisis.find_one({"slug":slugify(name)})

		if crisis is not None:
			flash("attention, ce sujet de crise existe déla",'danger')
			return redirect(url_for("admin.crisis"))

		else:
			
			db.crisis.insert_one({
				"name":name,
				"slug":slug,
				"audience":0,
				"is_active":is_active,
				"is_stick":is_stick,
				"create_at":datetime.datetime.utcnow(),
				"messages":[],
				"create_by":g.user["_id"]
			})

	flash("l'opération à bien été effectuée avec succes",'info')

	return redirect(url_for("admin.crisis"))


@bp.route("/crisis/delete", methods=('POST',))
@is_granted("role_super_admin")
@login_guard
def crisis_delete():
	"""
	supprimer un sujet de crise
	"""
	crisis_id = ObjectId(request.form["crisis_id"])

	
	crisis = db.crisis.aggregate([

		{
			"$match":{
				"_id":crisis_id
			}
		},
		{
			"$lookup":{
				"from":"consultation",
				"let":{"crisis_id":"$_id"},
				"pipeline":[
					{ 
						"$match":{
							"$expr":{
	                         	"$eq": [ "$crisis_id",  "$$crisis_id" ]
	                    	}
	                 	}
	              	},
	              	{
                 		"$group":{
                 			"_id":None,
                 			"total":{"$sum":1}
                 		}
	                },
	                {"$project":{"_id":0}}
				],
				"as":"tickets"
			}
		},
		
		{"$addFields":{"tickets":{"$arrayElemAt":["$tickets",0]}}},
		{"$addFields":{"tickets":"$tickets.total"}},
	])

	crisis = [i for i in crisis]

	if len(crisis):
		crisis = crisis[0]

	if crisis:
		if "tickets" in crisis:
			flash("attention ce sujet ne peut pas être supprimé car il a {} tickets a son actif".format(crisis['tickets']),'danger')
		else:
			db.crisis.delete_one({"_id":crisis_id})
			flash("le sujet à bien été supprimé avec succes",'info')

	return redirect(url_for("admin.crisis"))




@bp.route("/crisis/operators", methods=('GET','POST'))
@is_granted("role_super_admin")
@login_guard
def crisis_operators():
	"""
	onglet de gestion de crises pour gestion des operateurs
	"""

	

	data = db.crisis_operator.aggregate([
		{
			"$lookup":{
				"from":"user",
				"foreignField":"_id",
				"localField":"user_id",
				"as":"user"
			}
		},
		{
			"$lookup":{
				"from":"consultation",
				"let":{"operator_id":"$_id"},
				"pipeline":[
					{ 
						"$match":{
							"$expr":{
	                         	"$eq": [ "$operator_id",  "$$operator_id" ]
	                    	}
	                 	}
	              	},
	              	{
                 		"$group":{
                 			"_id":None,
                 			"total":{"$sum":1}
                 		}
	                },
	                {"$project":{"_id":0}}
				],
				"as":"tickets"
			}
		},
		{"$sort":{"_id":-1}},
		{"$limit":20},
		{"$addFields":{"user":{"$arrayElemAt":["$user",0]}}},
		{"$addFields":{"tickets":{"$arrayElemAt":["$tickets",0]}}},
		{"$addFields":{"tickets":"$tickets.total"}},
		{"$addFields":{"availablility_date":{"$add":["$user.last_presence",60*60*24*1000]}}},
		{"$addFields":{"is_available_for_ticket":{"$gte":["$availablility_date",datetime.datetime.utcnow()]}}},
	])

	data = [i for i in data]

	return render('admin/crisis-operator.html',data=data)

@bp.route("/crisis/operators/save", methods=('POST',))
@is_granted("role_super_admin")
@login_guard
def crisis_operator_save():
	"""
	enregistrer un operateur
	"""
	user_ids = []

	for i in request.form.getlist("user_ids"):
		user_ids.append(ObjectId(i))

	

	users = db.user.find({"_id":{"$in":user_ids}})

	for user in users:
		if db.crisis_operator.find_one({"user_id":user["_id"]}) is None:
			db.crisis_operator.insert_one({
				"user_id":user["_id"],
				"create_at":datetime.datetime.utcnow()
			})


	flash("l'opération à bien été effectuée avec succes",'info')

	return redirect(url_for("admin.crisis_operators"))

@bp.route("/crisis/operators/delete", methods=('POST',))
@is_granted("role_super_admin")
@login_guard
def crisis_operator_delete():
	"""
	supprimer un operateur
	"""
	operator_id = ObjectId(request.form["operator_id"])

	
	operator = db.crisis_operator.aggregate([

		{
			"$match":{
				"_id":operator_id
			}
		},
		{
			"$lookup":{
				"from":"consultation",
				"let":{"operator_id":"$_id"},
				"pipeline":[
					{ 
						"$match":{
							"$expr":{
	                         	"$eq": [ "$operator_id",  "$$operator_id" ]
	                    	}
	                 	}
	              	},
	              	{
                 		"$group":{
                 			"_id":None,
                 			"total":{"$sum":1}
                 		}
	                },
	                {"$project":{"_id":0}}
				],
				"as":"tickets"
			}
		},
		
		{"$addFields":{"tickets":{"$arrayElemAt":["$tickets",0]}}},
		{"$addFields":{"tickets":"$tickets.total"}},
	])

	operator = [i for i in operator]

	if len(operator):
		operator = operator[0]

	if operator:
		if "tickets" in operator:
			flash("attention cet opérateur ne peut pas être supprimé car il a {} tickets a son actif".format(operator['tickets']),'danger')
		else:
			db.crisis_operator.delete_one({"_id":operator_id})
			flash("l'opérateur à bien été supprimé avec succes",'info')

	return redirect(url_for("admin.crisis_operators"))



@bp.route("/crisis/operators/search", methods=('GET',))
@is_granted("role_super_admin")
@login_guard
def crisis_operator_search():
	"""
	recherche pour ajouter un operateur
	"""
	
	data = []
	q:str = request.args.get('term')
	if not q:
		return abort(404)


	stages = [

		{"$match":{
			"$text":{"$search":q},
		}},

		{"$lookup":{
			"from":"crisis_operator",
			"foreignField":"user_id",
			"localField":"_id",
			"as":"operator"
		}},


		{"$addFields":{"operator":{"$arrayElemAt":["$operator",0]}}},

		{"$match":{
			"operator":{"$exists":False}
		}},

		{"$project":{
			"_id":1,
			"first_name":1,
			"last_name":1,
			"profile_pic":1,
		}},

		{ "$sort": { "score": { "$meta": "textScore" } } },
		{"$limit":20}
	]


	d = db.user.aggregate(stages)
	d = [i for i in d]

	for el in d:
		for k,v in el.items():
			if isinstance(v, ObjectId):
				el[k] = str(v)


	r = response(json.dumps(d))
	r.headers["content-type"] = "application/json"

	return r,200


@bp.route("/crisis/tickets", methods=('GET','POST'))
@is_granted("role_super_admin")
@login_guard
def crisis_tickets():
	"""
	onglet de gestion de crises pour gestion des tickets
	"""

	

	data = db.consultation.aggregate([
		
		{
			"$lookup":{
				"from":"user",
				"foreignField":"_id",
				"localField":"user_id",
				"as":"user"
			}
		},
		
		{
			"$lookup":{
				"from":"crisis_operator",
				"foreignField":"_id",
				"localField":"operator_id",
				"as":"operator"
			}
		},
		{
			"$lookup":{
				"from":"user",
				"foreignField":"_id",
				"localField":"operator.user_id",
				"as":"user_operator"
			}
		},
		{"$sort":{"_id":-1}},
		{"$limit":20}
	])

	data = [i for i in data]


	for el in data:
		el["user"] = el["user"][0]
		if el["operator"]:
			el["operator"] = el["operator"][0]
			el["user_operator"] = el["user_operator"][0]


	return render('admin/crisis-ticket.html',data=data)


@bp.route("/crisis/tickets/<ticket_id>/messages", methods=('GET',))
@is_granted("role_super_admin")
@login_guard
def crisis_ticket_messages(ticket_id):
	"""
	charger les messages d'un ticket
	"""

	
	data = db.consultation.aggregate([

		{
			"$match":{
				"_id":ObjectId(ticket_id)
			}
		},
		{
			"$lookup":{
				"from":"user",
				"foreignField":"_id",
				"localField":"user_id",
				"as":"user"
			}
		},
		{
			"$lookup":{
				"from":"crisis_operator",
				"foreignField":"_id",
				"localField":"operator_id",
				"as":"operator"
			}
		},
		{
			"$lookup":{
				"from":"user",
				"foreignField":"_id",
				"localField":"operator.user_id",
				"as":"user_operator"
			}
		},
		{"$addFields":{"user":{"$arrayElemAt":["$user",0]}}},
		{"$addFields":{"operator":{"$arrayElemAt":["$operator",0]}}},
		{"$addFields":{"user_operator":{"$arrayElemAt":["$user_operator",0]}}},
	])

	data = [i for i in data]

	if len(data) == 0:
		return abort(404)


	# r = response(json.dumps(d))
	# r.headers["content-type"] = "application/json"

	return render('admin/crisis-ticket-messages.html',data=data[0])




@bp.route("/denunciations", methods=('GET','POST'))
@is_granted("role_super_admin")
@login_guard
def denunciations():
	"""
	onglet des denonciations
	"""
	
	data = db.denunciation.aggregate([
		{"$match":{
			"state":"submited",
			"user_id":{"$ne":None},
			"commune_id":{"$ne":None},
			"tag_id":{"$ne":None},
		}},
		
		{"$sort":{"create_at":-1}},
		{"$limit":20},
		{
			"$lookup":{
				"from":"user",
				"foreignField":"_id",
				"localField":"user_id",
				"as":"user"
			}
		},
		{
			"$lookup":{
				"from":"commune",
				"foreignField":"_id",
				"localField":"commune_id",
				"as":"commune"
			}
		},
		{
			"$lookup":{
				"from":"tag",
				"foreignField":"_id",
				"localField":"tag_id",
				"as":"tag"
			}
		},

		{"$addFields":{"user":{"$arrayElemAt":["$user",0]}}},
		{"$addFields":{"commune":{"$arrayElemAt":["$commune",0]}}},
		{"$addFields":{"tag":{"$arrayElemAt":["$tag",0]}}},

	])

	data = [i for i in data]

		
	return render('admin/denunciation-index.html', data=data)


@bp.route("/denunciations/<denunciation_id>", methods=('GET',))
@is_granted("role_super_admin")
@login_guard
def get_denunciation(denunciation_id):
	"""
	on recupere une denonciation
	"""
	
	data = db.denunciation.aggregate([
		{"$match":{
			"_id":ObjectId(denunciation_id),
			"state":"submited",
			"user_id":{"$ne":None},
			"commune_id":{"$ne":None},
			"tag_id":{"$ne":None},
		}},
		{
			"$lookup":{
				"from":"user",
				"foreignField":"_id",
				"localField":"user_id",
				"as":"user"
			}
		},
		{
			"$lookup":{
				"from":"commune",
				"foreignField":"_id",
				"localField":"commune_id",
				"as":"commune"
			}
		},
		{
			"$lookup":{
				"from":"tag",
				"foreignField":"_id",
				"localField":"tag_id",
				"as":"tag"
			}
		},

		{"$addFields":{"user":{"$arrayElemAt":["$user",0]}}},
		{"$addFields":{"commune":{"$arrayElemAt":["$commune",0]}}},
		{"$addFields":{"tag":{"$arrayElemAt":["$tag",0]}}},
	])

	data = [i for i in data]

	return render('admin/denunciation-modal-view.html', data=data)

@bp.route("/denunciation/tags", methods=('GET','POST'))
@is_granted("role_super_admin")
@login_guard
def denunciation_tags():
	"""
	onglet des denonciations gestion des etiquetes
	"""
	return render('admin/index.html')