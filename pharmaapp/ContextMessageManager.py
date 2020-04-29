#!/usr/bin/python3
# -*- coding:utf-8 -*-

import os
import time
import datetime
from pickle import Pickler,Unpickler
from enum import Enum
from copy import deepcopy
import random
import re
import requests
import pymongo
from bson.objectid import ObjectId
from slugify import slugify
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from flask import url_for

from .EventDispatcher import EventDispatcher
from .FBSend import FBSend
from .ContextUserManager import ContextUser
from .Consultation import Consultation

DATABASE_URL = os.environ["DATABASE_URL"]
client = pymongo.MongoClient(DATABASE_URL)
db = client.pharma_garde


		
class GIPHY:
	DEMO=["231306008034659"]

	GARDE_ALERT=[
		"2260208167610238", # image par defaut
		"465891990756816", # SEMAINE 4 JANVIER
		"2711408902278891", # SEMAINE DU 01 au 07 février
		"2377311519036686", # SEMAINE DU 08 au 14 février
		"2377311519036686", # SEMAINE DU 15 au 21 février
		"2555013097959484", # SEMAINE DU 22 au 28 février
		"886715755117525", # SEMAINE DU 29 fevrier au 06 mars
		"208789800372442", # SEMAINE DU 07 au 07 mars
		"822623314899049", # SEMAINE DU 21 au 27 MARS
	]

	HAPPY = [
		"675192166228243",
		"414734365796664",
		"343549249675765",
		"1140333469472949"
	]

	TYPING = [
		"714052079052451",
		"441456593072303",
		"347000079255675",
		"379146362714203"
	]

	WAITING = [
		"465060477372093",
		"366458980725111",
		"324627121810341",
		"896985843995660"
	]

	SUCCESS = [
		"2074683532839154",
		"2401705416775041",
		"315947775979920",
		"320844998791520"

	]

	THANKS = [
		"420514428537324",
		"307870286598983"
	]

	SAD = [
		"174248257237306",
		"2068381956640916",
		"190557095364759"
	]


class ContextCode(Enum):
	
	GET_STARTED = 0 # message de presentation du service
	HOME_MENU = 1 # message de presentation du menu principal
	HAPPY_TO_MEET = 2 # message qui dit "je suis ravi de faire ta connaissance"
	GOODBYE = 3 # message qui dit "aurevoir"
	GREETING = 4 # message qui dit "salut"
	GREETING_MORNING = 5 # message qui dit "bonjour"
	GREETING_EVENING = 6 # message qui dit "bonsoir"
	BOT_PRESENTATION = 7 # message qui presente le bot
	SAY_CAN_HELP_FIND_PHCIE = 8 # message qui dit "je peux vous trouver une pharmacie de garde"
	BLURFING = 9 # message qui fait les eloges du bot
	LOCALITIES_DISPLAY_SUGGEST = 10 # le bot propose d'afficher les localité
	NOTHING = 11  # message a ignorer
	NO_ANSWER = 12 # les messages par defaut dit "je ne comprends pas ce que vous demandez"
	VERBOSE = 13 # les messages intermediaire du bot
	RELANCE = 14 # des messages de relance sur une question pas encore posé
	NO_ACTION = 15  # reponse sans demande d'action
	CONFIRM_ANSWER = 16 # message de confirmation d'une question poseé par l'utilisateur
	IM_FINE = 17 # quand le bot repond " je vais bien "
	ASK_LOCALITY = 18 # quand le bot demande la localité du visiteur
	ANSWER_WITH_MY_NAME = 19 # quand le bot repond en disant son nom
	THANKS = 20 # quand le bot dit merci
	STREAMING_LOCALITIES = 21 # lorsque le bot est en train de repondre avec la liste des localités
	LOCALITY_ALERT = 22 # quand le bot rencontre probleme de lecteur des localités
	STREAMING_PHCIE = 23 # lorsque le bot est en train de repondre avec la liste des pharmacies
	IMAGE = 24 # lorsque le bot envoi une image,
	ASK_PHARMACY = 25
	SHARE = 26 # lorsque le bote envoi un partage,
	ASK_ZONE = 27 # quand le bot demande la zone de recherche du visiteur

	# quand le bot demande si le visiteur veut plus d'informations
	# sur une pharmacie
	ASK_PHARMACY_DETAILS = 28 
	# lorsque le bot demande a l'utilisateur de lui fournir la
	# situation géographique d'une pharmacie
	ASK_PHARMACY_LOC_TO_USER = 29 
	USER_PHARMACY_LOC_SUGGEST = 30
	# pour demander a l'utilisateur de s'abonner aux notifications d'une pharmacie
	PHARMACY_ALERT_SUBSCRIPTION = 31
	# pour demander a l'utilisateur de s'abonner aux notifications d'une localité
	LOCALITY_ALERT_SUBSCRIPTION = 32
	# le bot ouvre le menu a propos
	ABOUT_US = 33

class ContextMessageAuthor(Enum):
	USER = 1
	BOT = 2

class ContextMessage:
	"""

	"""
	def __init__(self,message=None,answered=None,required=False,code=None,author:ContextMessageAuthor = ContextMessageAuthor.BOT,is_question=False,_id=None):
		self._id = None
		self.code = code
		self.isQuestion = is_question
		self.answered = answered
		self.required = required
		self.create_at = datetime.datetime.today()
		self.message = message
		self.author:ContextMessageAuthor = author


	def hydrate(self,payload):
		for key,val in payload.items():
			if not key.startswith("__") and key in self.__dict__:
				if key == "code":
					val = ContextCode(val)
				elif key == "author":
					val = ContextMessageAuthor(val)
				setattr(self,key,val)

	def __repr__(self):
		return "<ContextMessage code={}, answered={}, required={}, create_at={}, author={}, message={} />".format(self.code,self.answered,self.required,self.create_at,self.author,self.message)

	def __call__(self):
		c = deepcopy(self)
		c._id = None
		return c


class ContextMessageManager(EventDispatcher):
	"""
	"""
	def __init__(self,user_id =  None):
		super().__init__()
		self._id = None
		# pour enregistrer la localité du visiteur
		self.currentLocation = None
		# le type de localité du visiteur soit commune ou quartier
		self.currentLocationType = None
		# la pharmacie recherchee pr le visiteur
		self.currentPharmacie = None
		# la zone de recherche soit 1 = Abidjan, 2 = Interieur du pays
		self.currentZone = None
		# la liste des pharmacies issue de la precedente recherche du visiteur
		self.oldDataSearch = None
		self.offsetDataSearch = 0
		# la liste des localités deja affichés du visiteur
		self.oldDataLocations = None
		self.offsetDataLocations = 0

		self.question_processing = None
		self.last_survey_id = None
		self.last_survey_offset = 0
		self.last_quizz_id = None
		self.last_quizz_offset = 0
		self.has_new_menu = False
		self.survey_one_time_notif_token = None
		self.quiz_one_time_notif_token = None
		self.pharmacy_one_time_notif_token = None


		# pour savoir si on a deja salué le visiteur
		self.handshake = False
		# pour savoir si on a deja dis aurevoir au visiteur
		self.goodbye = False 
		# pour savoir si on a deja dis le nom du bot au visiteur
		self.is_ask_name = False 
		# l'identifiant du visiteur
		self._user = ContextUser(user_id)
		# pour savoir ne nombre de question sans reponse predefenie
		self.fails = 0
		# pour savoir le nombre recherche reussi par l'utilisateur
		self.searchSuccess = 0
		# pour savoir ne nombre recherche non reussi par l'utilisateur
		self.searchFails = 0
		# la date et heure a partir de laquelle le chat a debuté
		self.create_at = datetime.datetime.today()
		# le timestamp de la derniere action effectuee dans la conversation
		self.last_presence = self.create_at
		self.rate = None

		# enregistre tout les messages de la conversation

		self._user.load()

		if self._user.psid is not None:
			self.reload()

	def hydrate(self,payload):
		for key,val in payload.items():
			if not key.startswith("__") and key in self.__dict__:
				setattr(self,key,val)

	def __repr__(self):
		return "<ContextMessageManager, currentLocation={}, fails={}, create_at={}, last_presence={} />".format(self.currentLocation,self.fails,self.create_at,self.last_presence)


	def load_messages(self):
		data = []
		if self._user._id:
			data = db.message.find(
				{"conversation_id":self._id},
			).limit(100).sort("create_at",-1)
		return data

	def get_conversation(self):
		date = datetime.date.today()
		current_date = datetime.datetime(date.year,date.month,date.day)
		conversation = db.conversation.find_one({
			"create_at":current_date,
			"user_id":self._user._id,
		})

		return conversation

	def create_conversation(self):
		date = datetime.date.today()
		current_date = datetime.datetime(date.year,date.month,date.day)

		_id = db.conversation.insert_one({
			"user_id":self._user._id,
			"currentLocation": None,
			"currentLocationType": None,
			"currentPharmacie": None,
			"currentZone": None,
			"oldDataSearch": None,
			"oldDataLocations": None,
			"offsetDataLocations":0,
			"handshake": None,
			"goodbye": None,
			"is_ask_name": None,
			"fails": None,
			"searchSuccess": 0,
			"searchFails": 0,
			"create_at": current_date,
			"last_presence": datetime.datetime.today()
		}).inserted_id

		return _id

	def reload(self):

		if self._user._id:
			# on charge la conversation
			conversation = self.get_conversation()
			if conversation:
				self.hydrate(conversation)
			else:
				_id = self.create_conversation()
				self._id = _id



	def save(self,payload=None):
		"""
		enregistrer un message dans la memoire
		"""
		data = {}
		u_data = {}

		u_key = ["currentLocation","currentPharmacie","currentZone","last_presence","rate","survey_one_time_notif_token","quiz_one_time_notif_token","pharmacy_one_time_notif_token","question_processing","last_survey_id","last_survey_offset","last_quizz_id","last_quizz_offset","has_new_menu"]

		if payload is None:
			for key in dir(self):
				if not key.startswith("_") and key in self.__dict__:
					data[key] = getattr(self,key)
					if key in u_key and data[key] is not None:
						u_data[key] = data[key]
						setattr(self._user,key,data[key])
						
					
		else:
			for key,val in payload.items():
				if not key.startswith("_") and key in self.__dict__:
					data[key] = val
					if key in u_key:
						u_data[key] = data[key]
						setattr(self._user,key,data[key])


		if len(data):
			db.conversation.update_one(
				{"_id":self._id},
				{"$set":data}
			)

		if len(u_data):

			db.user.update_one(
				{"_id":self._user._id},
				{"$set":u_data}
			)



	def addItem(self,item:ContextMessage):
		"""
		enregistrer un message dans la memoire
		"""
		assert isinstance(item,ContextMessage)

		db.message.insert_one({
			"conversation_id":self._id,
			"code":item.code.value,
			"isQuestion":item.isQuestion,
			"answered":item.answered,
			"required":item.required,
			"create_at":datetime.datetime.today(),
			"message":item.message,
			"author":item.author.value
		})
		db.conversation.update_one(
			{"_id":self._id},
			{"$set":{"last_presence":datetime.datetime.today()}}
		)


	def updateItem(self,contextCode:ContextCode,payload):
		"""
		mettre a jour les metadonnées d'un message
		"""
		db.message.update_one(
			{
				"conversation_id":self._id,
				"code":contextCode.value,
			},
			{"$set":payload}
		)

	def processConsultingFlow(self,message):
		"""
		traite les messages de consultations medicales
		"""
		how_talks = 0

		medecin = None
		req = db.consultation.find_one({
			"user_id":self._user._id,
			"state":1
		})

		if req is None:
			"""
			c'est le medecin qui parle
			"""
			medecin = db.medecin.find_one({
				"user_id":self._user._id
			})

			req = db.consultation.find_one({
				"medecin_id":medecin["_id"],
				"state":1
			})
			how_talks = 1

		cons = Consultation(data=req)
		cons.addMessage(message,how_talks)


	def handle_quick_reply(self,message):
		fbsend = FBSend()


		if "quick_reply" not in message:
			if self._user.question_processing is not None:
				message["quick_reply"] = {
					"payload":self._user.question_processing
				}

		
		if "quick_reply" in message:
			intent = []
			payload = message["quick_reply"]["payload"]


			if "entities" not in message["nlp"]:
				message["nlp"]["entities"] = {}  

			if payload == "GET_STARTED":
				fbsend.setPersitantMenu(self._user.psid)

				m = [
					"Hello {},\r\nJe suis Pharmabot 😎".format(self._user.first_name),
					"Hello {},\r\nJe m'appelle Pharmabot 😎".format(self._user.first_name),
					"Hello {},\r\nMon nom est Pharmabot 😎".format(self._user.first_name),
				]
				resp:dict = {"text":random.choice(m)}
				fbsend.sendMessage(self._user.psid,resp)

				m = [
					"Je t'aide à trouver une pharmacie de garde dans la localité de ton choix 🤗",
					"Ensemble, nous allons trouver une pharmacie de garde dans la localité de ton choix 🤗",
					"Nous allons trouver une pharmacie de garde dans la localité de ton choix, si tu suis attentivement mes instructions 😎",
				]

				resp:dict = {

					"attachment":{
						"type":"template",
						"payload": {
							"template_type":"button",
							"text":random.choice(m),
							"buttons":[
					    		{
						            "type":"postback",
						            "title":"👉DEMONSTRATION👈",
						            "payload":"START_DEMO",
						        }
					    	]
						}
					}
				}

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":None,
				})

				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"MAIN_MENU"
					},
					"insta":2
				}
				self.handle_quick_reply(m)
				return True


			elif payload == "COVID19_STATS":
				"""
				demande de statistiques sur le coronavirus
				"""

				opts = db.options.find_one({"name":"covid19"})
				in_cache = False
				result = None

				if opts["last_request_time"] is not None:
					delta = datetime.datetime.utcnow() - opts["last_request_time"]
					if delta.seconds//60 < 10:
						in_cache = True
						


				global_url = "https://www.worldometers.info/coronavirus/"
				ivory_url = "https://www.worldometers.info/coronavirus/country/cote-d-ivoire/"

				resp:dict = {
					"text":"{}, merci de respecter les mesures barrières.".format(self._user.first_name),
				}
				fbsend.sendMessage(self._user.psid,resp)
				
				if in_cache:
					result = opts["global_data"]
				else:
					result = self.load_covid19_stats(global_url);
					opts["global_data"] = result



				resp:dict = {
					"text":"Dans le monde Il y a environ:\r\n{} Cas\r\n{} Décès\r\n{} Rétablis".format(result["cases"],result["deaths"],result["recovered"]),
				}
				fbsend.sendMessage(self._user.psid,resp)

				if in_cache:
					result = opts["ivory_data"]
				else:
					result = self.load_covid19_stats(ivory_url);
					opts["ivory_data"] = result

				resp:dict = {
					"text":"En Côte d'Ivoire nous avons environ:\r\n{} Cas\r\n{} Décès\r\n{} Rétablis".format(result["cases"],result["deaths"],result["recovered"]),
				}
				fbsend.sendMessage(self._user.psid,resp)

				if in_cache == False:



					opts["last_request_time"] = datetime.datetime.utcnow()
					db.options.update_one({
						'_id':opts["_id"]
					},{
						"$set":{
							"last_request_time":opts["last_request_time"],
							"global_data":opts["global_data"],
							"ivory_data":opts["ivory_data"],
						}
					})

				self.save({
					"question_processing":None,
				})

				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"MAIN_MENU"
					},
					"insta":2
				}
				self.handle_quick_reply(m)

				return True

			elif payload == "OPTIN_QUIZZ_ALERT":
				"""
				abonnement à la newsletter
				"""
				optin_type = message["quick_reply"]["type"]
				one_time_notif_token = message["quick_reply"]["one_time_notif_token"]
				self.save({
					"quiz_one_time_notif_token":{
						"value":one_time_notif_token,
						"used":False
					}
				})

				resp:dict = {
					"text":"Félicitation, vous serez maintenant informé pour le prochain quizz",
				}
				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":None,
				})

				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"MAIN_MENU"
					},
					"insta":2
				}
				self.handle_quick_reply(m)

				return True


			elif payload == "QUIZZ_STARTED": 
				"""
				demarrage d'un quizz
				alors
				"""
				quizz = db.quizz.find_one({
					"_id":self._user.last_quizz_id
				})

				if quizz:
					new_offset = 0
					for i,el in enumerate(quizz["questions"]):
						if self._user.last_quizz_offset == i:
							new_offset = i+1

							resp:dict = {
								"text":"[Question ❓]\r\n"+el["payload"],
							}
							fbsend.sendMessage(self._user.psid,resp)

							quick_replies = []

							for pos,choice in enumerate(el["choices"]):

								num = 0
								if pos == 0:
									num = "1️⃣"
								elif pos == 1:
									num = "2️⃣"
								elif pos == 2:
									num = "3️⃣"
								elif pos == 3:
									num = "4️⃣"
								elif pos == 4:
									num = "5️⃣"

								resp:dict = {
									"text":"Reponse "+num+"\r\n"+choice["payload"],
								}
								fbsend.sendMessage(self._user.psid,resp)
								quick_replies.append({
									"content_type":"text",
									"title":"Reponse "+num,
									"payload":"QUIZZ_RESPONSE_"+str(choice["_id"])
								})


							resp:dict = {
								"text":"Selectionnez une reponse svp",
								"quick_replies":quick_replies
							}
							fbsend.sendMessage(self._user.psid,resp)

							break
				else:
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"MAIN_MENU"
						},
						"insta":2
					}
					self.handle_quick_reply(m)
					

				return True

			elif payload.startswith("QUIZZ_RESPONSE_"):
				"""
				l'utilisateur vient de selectionner une reponse dans un quizz
				"""

				quizz = db.quizz.find_one({
					"_id":self._user.last_quizz_id
				})

				if quizz:

					r = re.search(r"QUIZZ_RESPONSE_(.+)",payload)
					choice_id = ObjectId(r.group(1))
					question = quizz["questions"][self._user.last_quizz_offset]
					new_offset = self._user.last_quizz_offset + 1


					quizz_player = db.quizz_player.find_one({
						"quizz_id":quizz["_id"],
						"user_id":self._user._id
					})

						
					if quizz_player is None:
						quizz_player_id = db.quizz_player.insert_one({
							"quizz_id":quizz["_id"],
							"user_id":self._user._id,
							"started_at":datetime.datetime.utcnow(),
							"finished_at":None,
							"score":0,
							"offset":0
						}).inserted_id

						quizz_player = db.quizz_player.find_one({"_id":quizz_player_id})

					true_answer = None
					user_choice = None

					for i,question in enumerate(quizz["questions"]):
						if self._user.last_quizz_offset == i:
							for y,choice in enumerate(question["choices"]):
								if choice["is_true"]:
									true_answer = choice

								if choice["_id"] == choice_id:
									user_choice = choice

									if db.quizz_player_response.find_one({"quizz_player_id":quizz_player["_id"],"choice_id":choice["_id"]}) is None:

										db.quizz_player_response.insert_one({
											"quizz_player_id":quizz_player["_id"],
											"choice_id":choice["_id"],
											"create_at":datetime.datetime.utcnow(),
										})
								
							break

					if user_choice:
						self.save({
							"last_quizz_offset":new_offset,
						})

						update_payload = {
							"$set":{
								"offset":new_offset,
							}
						}

						text:str = ""
						filename:str = None

						if user_choice["_id"] == true_answer["_id"]:
							"""
							bonne reponse
							"""
							update_payload["$inc"] = {
								"score":1
							}

							if len(quizz["good_resp_gif_ids"]):
								 
								s_gif = random.choice(quizz["good_resp_gif_ids"])
								media = db.mediatheque.find_one({"_id":s_gif})
								filename = media["filename"]
							
							
							text = "Bonne reponse"

							if user_choice["autoresponder"]:
								text = text + "\r\n" + user_choice["autoresponder"]
							elif quizz["good_resp_txt"]:
								text = text + "\r\n" + quizz["good_resp_txt"]

						else:
							"""
							mauvaise reponse
							"""
							if len(quizz["bad_resp_gif_ids"]):
								s_gif = random.choice(quizz["bad_resp_gif_ids"])
								media = db.mediatheque.find_one({"_id":s_gif})
								filename = media["filename"]
						
							
							text = "Mauvaise reponse"

							if user_choice["autoresponder"]:
								text = text + "\r\n" + user_choice["autoresponder"]
							elif quizz["good_resp_txt"]:
								text = text + "\r\n" + quizz["bad_resp_txt"]


						resp:dict = {
							"text":text,
						}
						fbsend.sendMessage(self._user.psid,resp)

						if filename :
							filename = "mediatheque/{}".format(filename)
							resp:dict = {
								"attachment": {
					            	"type": "image",
					                "payload": {
					                    "url": url_for("static", filename=filename, _external=True)
					                }
								}
							}
							fbsend.sendMessage(self._user.psid,resp)
						

						db.quizz_player.update_one({
							"_id":quizz_player["_id"]
						},update_payload)

						self._user.last_quizz_offset = new_offset


						if new_offset >= len(quizz["questions"]):
							"""
							le questionnaire vient d'etre epuisé
							on met fin à ce quizz
							"""
							if quizz_player["finished_at"] is None:
								db.quizz_player.update_one({
									"_id":quizz_player["_id"]
								},{
									"$set":{
										"finished_at":datetime.datetime.utcnow(),
									}
								})

							step = quizz["score"]/2
							text:str = ""
							filename = None

							if quizz["score"] == 0:
								text = "aucune bonne reponse"

							elif quizz["score"] == 1:
								text = "1 seule bonne reponse"

							else:
								text = "{} bonnes reponses".format(quizz["score"])


							if quizz["score"] >= len(quizz["questions"])//2 :
								"""
								message pour une note au dessus de la moyenne
								"""

								if "above_mean_txt" in quizz and quizz["above_mean_txt"]:
									resp:dict = {
										"text":quizz["above_mean_txt"],
									}
									fbsend.sendMessage(self._user.psid,resp)

								if len(quizz["above_mean_gif_ids"]):
									s_gif = random.choice(quizz["above_mean_gif_ids"])
									media = db.mediatheque.find_one({"_id":s_gif})
									filename = media["filename"]

								elif len(quizz["good_resp_gif_ids"]):
									s_gif = random.choice(quizz["good_resp_gif_ids"])
									media = db.mediatheque.find_one({"_id":s_gif})
									filename = media["filename"]


							else:
								"""
								message pour une note en dessous de la moyenne
								"""

								if "below_mean_txt" in quizz and quizz["below_mean_txt"]:
									resp:dict = {
										"text":quizz["below_mean_txt"],
									}
									fbsend.sendMessage(self._user.psid,resp)

								if len(quizz["below_mean_gif_ids"]):
									s_gif = random.choice(quizz["below_mean_gif_ids"])
									media = db.mediatheque.find_one({"_id":s_gif})
									filename = media["filename"]

								elif len(quizz["bad_resp_gif_ids"]):
									s_gif = random.choice(quizz["bad_resp_gif_ids"])
									media = db.mediatheque.find_one({"_id":s_gif})
									filename = media["filename"]



							if filename:
								filename = "mediatheque/{}".format(filename)
								resp:dict = {
									"attachment": {
						            	"type": "image",
						                "payload": {
						                    "url": url_for("static", filename=filename, _external=True)
						                }
									}
								}
								fbsend.sendMessage(self._user.psid,resp)


							if quizz["end_text"]:
								resp:dict = {
									"text":quizz["end_text"],
								}
								fbsend.sendMessage(self._user.psid,resp)

							
							# resp:dict = {
							# 	"text":"merci d'avoir participé a ce quizz\r\npour ne rien manquer, abonne toi pour être informé pour les prochains quizz."
							# }
							# fbsend.sendMessage(self._user.psid,resp)

							# resp:dict = {
							# 	"attachment": {
							#     	"type":"template",
							#       	"payload": {
							#         	"template_type":"one_time_notif_req",
							#         	"title":"Quizz Alerte",
							#         	"payload":"OPTIN_QUIZZ_ALERT"
							#       }
							#     }
							# }
							# fbsend.sendMessage(self._user.psid,resp)
							self.save({
								"question_processing":None,
							})
						else:
							message["quick_reply"]["payload"] = "QUIZZ_STARTED"
							message["insta"] = 2
							return self.handle_quick_reply(message)

				else:
					"""
					si ne quizz n'existe plus ou pas il faut revenir
					au menu principal
					"""
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"MAIN_MENU"
						},
						"insta":2
					}
					self.handle_quick_reply(m)


				return True

			elif payload.startswith("QUIZZ_SELECT_"):
				"""
				l'utilisateur vient de selectionner un quizz
				"""

				r = re.search(r"QUIZZ_SELECT_(.+)",payload)
				quizz_id = r.group(1)
				quizz = None

				if quizz_id == "CURRENT":
					quizz = db.quizz.find({
						"is_active":True
					}).sort("_id",-1).limit(1)

					if quizz:
						quizz = quizz[0]
						quizz_id = str(quizz["_id"])
				else:
					quizz = db.quizz.find_one({
						"_id":ObjectId(quizz_id)
					})

				if quizz:

					media = None

					if "cover_id" in quizz:
						media = db.mediatheque.find_one({"_id":quizz["cover_id"]})

					if media:
						filename = media["filename"]
						filename = "mediatheque/{}".format(filename)
						resp:dict = {
							"attachment": {
				            	"type": "image",
				                "payload": {
				                    "url": url_for("static", filename=filename, _external=True)
				                }
							}
						}
						fbsend.sendMessage(self._user.psid,resp)
					else:
						resp:dict = {
							"text":"[Enquête 📊]\r\n"+quizz["title"],
						}
						fbsend.sendMessage(self._user.psid,resp)


					if quizz["welcome_text"]:
						resp:dict = {
							"text":quizz["welcome_text"],
						}
						fbsend.sendMessage(self._user.psid,resp)


					self.save({
						"question_processing":"QUIZZ_STARTED",
						"last_quizz_id":quizz["_id"],
						"last_quizz_offset":0,
					})

					self._user.last_quizz_id = quizz["_id"]
					self._user.last_quizz_offset = 0

					message["quick_reply"]["payload"] = "QUIZZ_STARTED"
					message["insta"] = 2
					return self.handle_quick_reply(message)

				else:
					"""
					si ne quizz n'existe plus ou pas il faut revenir
					au menu principal
					"""
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"MAIN_MENU"
						},
						"insta":2
					}
					self.handle_quick_reply(m)

				return True

			elif payload == "QUIZZ_LIST": 
				"""
				presentation de la liste des quizz en cours
				"""

				if "insta" not in message:
					text:str = "Enquêtes en cours"
					resp:dict = {
						"text":text,
					}
					fbsend.sendMessage(self._user.psid,resp)

				quizzs = db.quizz.find({
					"is_active":True,
					"is_closed":False
				}).sort("_id",-1).limit(5)

				quizzs = [i for i in quizzs]

				if len(quizzs) == 0:

					text:str = "Je n'ai pas de quizz pour l'heure, veux-tu être informé dès disponibilité ?"
					resp:dict = {
						"text":text,
					}
					fbsend.sendMessage(self._user.psid,resp)

					resp:dict = {
						"attachment": {
					    	"type":"template",
					      	"payload": {
					        	"template_type":"one_time_notif_req",
					        	"title":"Quizz Alerte",
					        	"payload":"OPTIN_QUIZZ_ALERT"
					      }
					    }
					}

					fbsend.sendMessage(self._user.psid,resp)
					self.save({
						"question_processing":None,
					})

				else:
					quick_replies = []
					for i,el in enumerate(quizzs):
						num = 0
						if i == 0:
							num = "1️⃣"
						elif i == 1:
							num = "2️⃣"
						elif i == 2:
							num = "3️⃣"
						elif i == 3:
							num = "4️⃣"
						elif i == 4:
							num = "5️⃣"

						text = num + " " + el["title"]
						resp:dict = {
							"text":text,
						}

						quick_replies.append({
							"content_type":"text",
							"title":text,
							"payload":"QUIZZ_SELECT_"+str(el["_id"])
						})

						fbsend.sendMessage(self._user.psid,resp)

					text:str = "Voulez-vous participer à quelle enquête ?"
					resp:dict = {
						"text":text,
						"quick_replies":quick_replies
					}
					fbsend.sendMessage(self._user.psid,resp)

					self.save({
						"question_processing":"QUIZZ_LIST"
					})

				return True

			#######################



			elif payload == "OPTIN_SURVEY_ALERT":
				"""
				abonnement à la newsletter
				"""
				optin_type = message["quick_reply"]["type"]
				one_time_notif_token = message["quick_reply"]["one_time_notif_token"]
				self.save({
					"survey_one_time_notif_token":{
						"value":one_time_notif_token,
						"used":False
					}
				})

				resp:dict = {
					"text":"Félicitation, vous serez maintenant informé pour le prochain sondage",
				}
				fbsend.sendMessage(self._user.psid,resp)

				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"MAIN_MENU"
					},
					"insta":2
				}
				self.handle_quick_reply(m)

				return True

			

			elif payload == "SURVEY_STARTED": 
				"""
				demarrage d'un sondage
				"""

				survey = db.survey.find_one({
					"_id":self._user.last_survey_id
				})

				if survey:
					new_offset = 0
					for i,el in enumerate(survey["questions"]):
						if self._user.last_survey_offset == i:
							new_offset = i+1

							resp:dict = {
								"text":"[Question ❓]\r\n"+el["payload"],
							}
							fbsend.sendMessage(self._user.psid,resp)

							quick_replies = []

							for pos,choice in enumerate(el["choices"]):

								num = 0
								if pos == 0:
									num = "1️⃣"
								elif pos == 1:
									num = "2️⃣"
								elif pos == 2:
									num = "3️⃣"
								elif pos == 3:
									num = "4️⃣"
								elif pos == 4:
									num = "5️⃣"

								resp:dict = {
									"text":"Reponse "+num+"\r\n"+choice["payload"],
								}
								fbsend.sendMessage(self._user.psid,resp)
								quick_replies.append({
									"content_type":"text",
									"title":"Reponse "+num,
									"payload":"SURVEY_RESPONSE_"+str(choice["_id"])
								})


							resp:dict = {
								"text":"Selectionnez une reponse svp",
								"quick_replies":quick_replies
							}
							fbsend.sendMessage(self._user.psid,resp)

							break

				else:
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"MAIN_MENU"
						},
						"insta":2
					}
					self.handle_quick_reply(m)

				return True

			elif payload.startswith("SURVEY_RESPONSE_"):
				"""
				l'utilisateur vient de selectionner une reponse dans un sondage
				"""

				survey = db.survey.find_one({
					"_id":self._user.last_survey_id
				})

				if survey:

					r = re.search(r"SURVEY_RESPONSE_(.+)",payload)
					choice_id = ObjectId(r.group(1))
					question = survey["questions"][self._user.last_survey_offset]
					new_offset = self._user.last_survey_offset + 1

					print(new_offset,len(survey["questions"]))

					if new_offset >= len(survey["questions"]):
						"""
						le questionnaire vient d'etre epuisé
						on met fin à ce sondage
						"""

						resp:dict = {
							"text":"merci d'avoir participé a ce quizz\r\npour ne rien manquer, abonne toi pour être informé pour les prochains sondages."
						}
						fbsend.sendMessage(self._user.psid,resp)

						resp:dict = {
							"attachment": {
						    	"type":"template",
						      	"payload": {
						        	"template_type":"one_time_notif_req",
						        	"title":"Sondages Alerte",
						        	"payload":"OPTIN_SURVEY_ALERT"
						      }
						    }
						}
						print(fbsend.sendMessage(self._user.psid,resp).json())
						self.save({
							"question_processing":None,
						})

					else:

						is_exists = []
						if "users" in survey:
							is_exists = [i for i in survey["users"] if i["_id"] == self._user._id]
						
						if len(is_exists) == 0:
							db.survey.update_one({
								"_id":survey["_id"]
							},{
								"$push":{
									"users":{
										"_id":self._user._id,
										"finish_at":None,
										"startd_at":datetime.datetime.utcnow()
									}
								}
							})


						for i,question in enumerate(survey["questions"]):
							if self._user.last_survey_offset == i:
								for y,choice in enumerate(question["choices"]):
									if choice["_id"] == choice_id:
										total = survey["questions"][i]["choices"][y]["answers"]
										survey["questions"][i]["choices"][y]["answers"] = total+1

										db.survey.update_one({
											"_id":survey["_id"],
										},{
											"$set":{"questions":survey["questions"]}
										})
										break
									
								break

						self.save({
							"last_survey_offset":new_offset,
						})

						self._user.last_survey_offset = new_offset
						message["quick_reply"]["payload"] = "SURVEY_STARTED"
						message["insta"] = 2
						return self.handle_quick_reply(message)

				else:
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"MAIN_MENU"
						},
						"insta":2
					}
					self.handle_quick_reply(m)


				return True

			elif payload.startswith("SURVEY_SELECT_"):
				"""
				l'utilisateur vient de selectionner un sondage
				"""

				r = re.search(r"SURVEY_SELECT_(.+)",payload)
				survey_id = r.group(1)
				survey = None

				if survey_id == "CURRENT":
					survey = db.survey.find({
						"is_active":True
					}).sort("_id",-1).limit(1)

					if survey:
						survey = survey[0]
						survey_id = str(survey["_id"])
				else:
					survey = db.survey.find_one({
						"_id":ObjectId(survey_id)
					})

				if survey:

					resp:dict = {
						"text":"[Enquête 📊]\r\n"+survey["title"],
					}
					fbsend.sendMessage(self._user.psid,resp)

					self.save({
						"question_processing":"SURVEY_STARTED",
						"last_survey_id":survey["_id"],
						"last_survey_offset":0,
					})

					self._user.last_survey_id = survey["_id"]
					self._user.last_survey_offset = 0

					message["quick_reply"]["payload"] = "SURVEY_STARTED"
					message["insta"] = 2
					return self.handle_quick_reply(message)

				else:
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"MAIN_MENU"
						},
						"insta":2
					}
					self.handle_quick_reply(m)

				return True

			elif payload == "SURVEY_LIST": 
				"""
				presentation de la liste des sondages en cours
				"""

				if "insta" not in message:
					text:str = "Enquêtes en cours"
					resp:dict = {
						"text":text,
					}
					fbsend.sendMessage(self._user.psid,resp)

				surveys = db.survey.find({
					"is_active":True,
					"is_closed":False
				}).sort("_id",-1).limit(5)


				surveys = [i for i in surveys]


				if len(surveys) == 0:

					text:str = "Je n'ai pas de sondages pour l'heure, veux-tu être informé dès disponibilité ?"
					resp:dict = {
						"text":text,
					}
					fbsend.sendMessage(self._user.psid,resp)

					resp:dict = {
						"attachment": {
					    	"type":"template",
					      	"payload": {
					        	"template_type":"one_time_notif_req",
					        	"title":"Sondages Alerte",
					        	"payload":"OPTIN_SURVEY_ALERT"
					      }
					    }
					}

					fbsend.sendMessage(self._user.psid,resp)
					self.save({
						"question_processing":None,
					})
				else:
					quick_replies = []
					for i,el in enumerate(surveys):
						num = 0
						if i == 0:
							num = "1️⃣"
						elif i == 1:
							num = "2️⃣"
						elif i == 2:
							num = "3️⃣"
						elif i == 3:
							num = "4️⃣"
						elif i == 4:
							num = "5️⃣"

						text = num + " " + el["title"]
						resp:dict = {
							"text":text,
						}

						quick_replies.append({
							"content_type":"text",
							"title":text,
							"payload":"SURVEY_SELECT_"+str(el["_id"])
						})

						fbsend.sendMessage(self._user.psid,resp)

					text:str = "Voulez-vous participer à quelle enquête ?"
					resp:dict = {
						"text":text,
						"quick_replies":quick_replies
					}
					fbsend.sendMessage(self._user.psid,resp)

					self.save({
						"question_processing":"SURVEY_LIST"
					})

				return True

			elif payload == "CONSULTATION_REQUEST":
				"""
				il s'agit d'une demande de consultation
				"""
				req = Consultation(self._user._id)
				req.run()

				return True

			elif payload.startswith("CONSULTATION_REFUSED_"):
				"""
				il s'agit d'un refus de demande de consultation
				"""
				r = re.search(r"CONSULTATION_REFUSED_(.+)",payload)
				consult_id = r.group(1)

				req = db.consultation.find_one({
					"_id":ObjectId(consult_id)
				})

				if req:

					consultation = Consultation(data=req)
					consultation.refuse()


				return True

			elif payload.startswith("CONSULTATION_ACCEPTED_"):
				"""
				il s'agit d'un ok pour demande de consultation
				"""
				r = re.search(r"CONSULTATION_ACCEPTED_(.+)",payload)
				consult_id = r.group(1)

				req = db.consultation.find_one({
					"_id":ObjectId(consult_id)
				})

				if req:
					cons = Consultation(data=req)
					cons.accept()
				else:
					resp:dict = {
						"text":"Dr. {} cette demande de consultation a expirée".format(self._user.first_name)
					}
					fbsend.sendMessage(self._user.psid,resp)

					resp:dict = {
						"text":"Dr. {} merci pour l'intéret que vous portez à ce projet".format(self._user.first_name)
					}
					fbsend.sendMessage(self._user.psid,resp)

				return True

			elif payload.startswith("CONSULTATION_CLOSE_"):
				"""
				il s'agit d'un refus de demande de consultation
				"""
				r = re.search(r"CONSULTATION_CLOSE_(.+)",payload)
				consult_id = r.group(1)

				req = db.consultation.find_one({
					"_id":ObjectId(consult_id)
				})

				if req:

					consultation = Consultation(data=req)
					consultation.finish()


				return True

			elif payload == "START_DEMO":
				resp:dict = {
					"attachment": {
		            	"type": "video",
		                "payload": {
		                    "attachment_id": random.choice(GIPHY.DEMO),
		                }
					}
				}
				fbsend.sendMessage(self._user.psid,resp)

				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"MAIN_MENU"
					},
					"insta":2
				}
				self.handle_quick_reply(m)
				return True

			elif payload in ["FAQ_HOW_IT_WORKS","HOW_IT_WORKS"]:

				m = [
					"Phamabot t'aide à trouver une pharmacie de garde dans la localité de ton choix 😎"

				]
				resp:dict = {"text":random.choice(m)}
				fbsend.sendMessage(self._user.psid,resp)

				text = 'Dans un premier temps\r\nTu devras m\'aider à me souvenir de 2 élements tres important:\r\n\r\n1.Ta zone soit "Abidjan" ou "Intérieur du pays"\r\n2. Ta localité qui est une commune.'
				
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				text = 'Ces 2 élements te seront présentés dans une liste pour enregistrer ton choix.'
				
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)


				text = "A toute fin utile,\r\nTu peux t'abonner aux tours de gardes d'une localité pour recevoir à chaque période les pharmacies de garde de cette localité en message privée"
				
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				text = "Ayant le souci d'aider au mieux mes utilisateurs, je demande tres souvent aux personnes comme toi {} de me proposer la situation géographique precise d'une pharmacie consultée ici 😉".format(self._user.first_name)
				
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				self.save({"question_processing":None})

				text = "J'espère n'avoir pas été trop ennuyant 🏃‍♂️"
				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"MAIN_MENU" if payload == "HOW_IT_WORKS" else "ABOUT_US_FAQ"
					},
					"insta":0
				}
				self.handle_quick_reply(m)
				return True

			elif payload in ["FAQ_AVAILABLE_COUNTRIES","FAQ_MEDECIN_PURCHASE","FAQ_MEDECIN_DELIVERY","FAQ_ALERTE_SUBSCRIPTION","FAQ_SHOW_SUBSCRIPTIONS","FAQ_CONSULTATION"]:

				elts = ["FAQ_AVAILABLE_COUNTRIES","FAQ_MEDECIN_PURCHASE","FAQ_MEDECIN_DELIVERY","FAQ_ALERTE_SUBSCRIPTION","FAQ_SHOW_SUBSCRIPTIONS","FAQ_CONSULTATION"]

				m = [
					"Section en cours d'écriture 🧐"
				]
				resp:dict = {"text":random.choice(m)}
				fbsend.sendMessage(self._user.psid,resp)

				self.save({"question_processing":None})

				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"ABOUT_US_FAQ"
					},
					"insta": elts.index(payload)+1
				}
				self.handle_quick_reply(m)

				return True

			elif payload == "ABOUT_US":
				text:str = "Bienvenue {},\r\nJe suis ton assistant personnel de pharmacies de gardes.\r\nJe t'accompagne dans la recherche de pharmacies de gardes dans la localité de ton choix".format(self._user.first_name)
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				text:str = "Que Souhaites-tu savoir {} ?".format(self._user.first_name)
				resp:dict = {
					"text":text,
					"quick_replies":[
						{
							"content_type":"text",
							"title":"Pourquoi Pharmabot ❓",
							"payload":"ABOUT_US_WHY_PHARMABOT"
						},
						{
							"content_type":"text",
							"title":"L'équipe 👨‍👨‍👦‍👦",
							"payload":"ABOUT_US_TEAM"
						},
						{
							"content_type":"text",
							"title":"F.A.Q 📖",
							"payload":"ABOUT_US_FAQ"
						},
						{
							"content_type":"text",
							"title":"Contact 💬",
							"payload":"ABOUT_US_CONTACT"
						},
						{
							"content_type":"text",
							"title":"Menu principal",
							"payload":"MAIN_MENU"
						}
					]
				}
				fbsend.sendMessage(self._user.psid,resp)
				self.save({"question_processing":"ABOUT_US"})
				return True

			elif payload == "ABOUT_US_WHY_PHARMABOT":
				text:str = "Pharmabot est né d'un constat.\r\nLes informations des tours de gardes sont disponibles çà et là sur des plateformes attendant d'être consultées."
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				text:str = "Même si l'information existe, il faut dans un premier temps savoir où elle se trouve et enfin aller la chercher.\r\ncela devient tres vite fastidieux car on y perd tres souvent du temps."
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				text:str = "De là, est né l'idée d'accompagner les personnes désireuses de recevoir directement les alertes des tours de gardes dans leur localité et ce, de manière intuitive et innonvante 😍"
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				text:str = "depuis le mois de juillet 2019, Pharmabot est né mettant à disposition les tours de gardes mais aussi les consultations médicales en ligne assurées par des medecins et pharmaciens bénévoles."
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)


				text:str = "Un autre sujet t'intéresse ?"
				resp:dict = {
					"text":text,
					"quick_replies":[
						{
							"content_type":"text",
							"title":"L'équipe 👨‍👨‍👦‍👦",
							"payload":"ABOUT_US_TEAM"
						},
						{
							"content_type":"text",
							"title":"F.A.Q 📖",
							"payload":"ABOUT_US_FAQ"
						},
						{
							"content_type":"text",
							"title":"Contact 💬",
							"payload":"ABOUT_US_CONTACT"
						},
						{
							"content_type":"text",
							"title":"Menu principal 🔎",
							"payload":"MAIN_MENU"
						}
					]
				}
				fbsend.sendMessage(self._user.psid,resp)
				self.save({"question_processing":None})

				return True


			elif payload == "ABOUT_US_TEAM":

				resp:dict = {
					"attachment":{
						"type":"template",
						"payload": {
							"template_type":"generic",
							"elements": [
							    {
							    	"title": "Zacharie A. Assagou",
							  		"subtitle":"Développeur & Founder",
							  		"image_url":"https://cipharmabot.herokuapp.com/static/founder.jpg",
							    	"buttons":[
							    		{
								            "type":"web_url",
								            "title":"CONTACTER",
								            "url":"https://www.linkedin.com/in/sagouRitchie",
								        }
							    	]
							    }
							]
						}
					}
				}
				fbsend.sendMessage(self._user.psid,resp)

				text:str = "Une autre question ?"
				resp:dict = {
					"text":text,
					"quick_replies":[
						{
							"content_type":"text",
							"title":"Pourquoi Pharmabot ❓",
							"payload":"ABOUT_US_WHY_PHARMABOT"
						},
						{
							"content_type":"text",
							"title":"Contact 💬",
							"payload":"ABOUT_US_CONTACT"
						},
						{
							"content_type":"text",
							"title":"Menu principal 🔎",
							"payload":"MAIN_MENU"
						}
					]
				}
				fbsend.sendMessage(self._user.psid,resp)
				self.save({"question_processing":None})


				return True

			elif payload == "ABOUT_US_FAQ":

				if "insta" not in message:
					text:str = 'Ci-dessous une liste de questions fréquemment posées, clique sur "Voir réponse" si tu veux en savoir plus 😉'
					resp:dict = {"text":text}
					fbsend.sendMessage(self._user.psid,resp)

				elements:list = [
				    {
				    	"title": "Comment ça marche ?",
				    	"buttons":[
				    		{
					            "type":"postback",
					            "title":"VOIR REPONSE",
					            "payload":"FAQ_HOW_IT_WORKS",
					        }
				    	]
				    },
				    {
				    	"title": "Pourquoi le Chatbot est disponible qu'en Côte d'Ivoire ?",
				    	"buttons":[
				    		{
					            "type":"postback",
					            "title":"VOIR REPONSE",
					            "payload":"FAQ_AVAILABLE_COUNTRIES",
					        }
				    	]
				    },
				    {
				    	"title": "Pourquoi Phamabot ne propose pas de medicaments ?",
				    	"buttons":[
				    		{
					            "type":"postback",
					            "title":"VOIR REPONSE",
					            "payload":"FAQ_MEDECIN_PURCHASE",
					        }
				    	]
				    },
				    {
				    	"title": "J'ai une une ordonnance médicale que faire ?",
				    	"buttons":[
				    		{
					            "type":"postback",
					            "title":"VOIR REPONSE",
					            "payload":"FAQ_MEDECIN_DELIVERY",
					        }
				    	]
				    },
				    {
				    	"title": "Comment s'abonner aux alertes d'une localité ?",
				    	"buttons":[
				    		{
					            "type":"postback",
					            "title":"VOIR REPONSE",
					            "payload":"FAQ_ALERTE_SUBSCRIPTION",
					        }
				    	]
				    },
				    {
				    	"title": "Comment afficher mes abonnements ?",
				    	"buttons":[
				    		{
					            "type":"postback",
					            "title":"VOIR REPONSE",
					            "payload":"FAQ_SHOW_SUBSCRIPTIONS",
					        }
				    	]
				    },
				    {
				    	"title": "Les consultations, c'est possible ?",
				    	"buttons":[
				    		{
					            "type":"postback",
					            "title":"VOIR REPONSE",
					            "payload":"FAQ_CONSULTATION",
					        }
				    	]
				    }
				]

				if "insta" in message:
					del elements[message["insta"]]


				resp:dict = {
					"attachment":{
						"type":"template",
						"payload": {
							"template_type":"generic",
							"elements": elements
						}
					}
				}
				fbsend.sendMessage(self._user.psid,resp)


				text:str = "Envie d'en savoir plus sur..."
				resp:dict = {
					"text":text,
					"quick_replies":[
						{
							"content_type":"text",
							"title":"Pourquoi Pharmabot ❓",
							"payload":"ABOUT_US_WHY_PHARMABOT"
						},
						{
							"content_type":"text",
							"title":"L'équipe 👨‍👨‍👦‍👦",
							"payload":"ABOUT_US_TEAM"
						},
						{
							"content_type":"text",
							"title":"Contact 💬",
							"payload":"ABOUT_US_CONTACT"
						},
						{
							"content_type":"text",
							"title":"Menu principal",
							"payload":"MAIN_MENU"
						}
					]
				}
				fbsend.sendMessage(self._user.psid,resp)
				self.save({"question_processing":None})

				return True

			elif payload == "ABOUT_US_CONTACT":
				text:str = "{}, J'apprecirais recevoir ton retour d'experience, qu'il soit bon ou mauvais.\r\nCela m'aide tous les jours à me développer 💓".format(self._user.first_name)
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				text:str = "Si jamais tu veux contacter l'équipe derrière ma conception, il sont vraiment ouvert 😉"
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				text:str = "N'hésite surtout pas à nous envoyer un mail à cipharmabot@gmail.com"
				resp:dict = {"text":text}
				fbsend.sendMessage(self._user.psid,resp)

				text:str = "Une autre question ?"
				resp:dict = {
					"text":text,
					"quick_replies":[
						{
							"content_type":"text",
							"title":"Pourquoi Pharmabot ❓",
							"payload":"ABOUT_US_WHY_PHARMABOT"
						},
						{
							"content_type":"text",
							"title":"L'équipe 👨‍👨‍👦‍👦",
							"payload":"ABOUT_US_TEAM"
						},
						{
							"content_type":"text",
							"title":"F.A.Q 📖",
							"payload":"ABOUT_US_FAQ"
						},
						{
							"content_type":"text",
							"title":"Menu principal",
							"payload":"MAIN_MENU"
						}
					]
				}
				fbsend.sendMessage(self._user.psid,resp)
				self.save({"question_processing":None})

				return True

			elif payload == "MY_LOCALITIES_SUBSCRIPTION":
				"""
				on affiche les localités auquelles l'utilisateur a souscrite
				"""
				sub_loc = 0

				if self._user.preferred_localities:
					sub_loc = len(self._user.preferred_localities)

				text:str = ""

				if sub_loc:

					if sub_loc > 1:
						text = "{}, tu es abonné aux alertes des localités suivantes:".format(self._user.first_name)
					else:
						text = "{}, tu es abonné aux alertes de la localité suivante:".format(self._user.first_name)
				else:
					text = "{}, tu n'a aucun abonnement de localité pour le moment\r\nje te prie de faire une recherche pour t'abonner".format(self._user.first_name)

				resp:dict = {
					"text":text,
				}

				if sub_loc == 0:
					resp["quick_replies"] = [
						{
							"content_type":"text",
							"title":"🔎 Menu principal",
							"payload":"MAIN_MENU"
						}
					]

				fbsend.sendMessage(self._user.psid,resp)

				if sub_loc:
					text = ""
					for i,v in enumerate(self._user.preferred_localities):
						if v["subscribed"] == True:
							text += "📍 {}\r\n".format(v["name"])
					
					resp:dict = {
						"text":text,
						"quick_replies":[
							{
								"content_type":"text",
								"title":"🔎 Nouvelle recherche",
								"payload":"MAIN_MENU"
							}
						]
					}
					fbsend.sendMessage(self._user.psid,resp)

				self.save({"question_processing":None})
				return True

			elif payload == "MY_PHARMACIES_SUBSCRIPTION":
				"""
				on affiche les pharmacies auquelles l'utilisateur à souscrite
				"""

				sub_loc = 0
				if self._user.preferred_pharmacies:
					sub_loc = len(self._user.preferred_pharmacies)

				text:str = ""

				if sub_loc:

					if sub_loc > 1:
						text = "{}, tu es abonné aux alertes des pharmacies suivantes:".format(self._user.first_name)
					else:
						text = "{}, tu es abonné aux alertes de la pharmacies suivante:".format(self._user.first_name)
				else:
					text = "{}, tu n'a aucun abonnement de pharmacie pour le moment\r\nje te prie de faire une recherche pour t'abonner".format(self._user.first_name)

				resp:dict = {
					"text":text,
				}

				if sub_loc == 0:
					resp["quick_replies"] = [
						{
							"content_type":"text",
							"title":"🔎 Menu principal",
							"payload":"MAIN_MENU"
						}
					]
					
				fbsend.sendMessage(self._user.psid,resp)

				if sub_loc:
					text = ""
					for i,v in enumerate(self._user.preferred_pharmacies):
						if v["subscribed"] == True:
							text = "🏫 {}\r\n📍 {}".format(v["name"].title(),v["locality"].title())

							resp:dict = {
								"text":text,
							}

							fbsend.sendMessage(self._user.psid,resp)

					resp:dict = {
						"text":"Tu seras informé pour chaque période lorsque l'une de ces pharmacies sera oui ou non de garde 💪",
						"quick_replies":[
							{
								"content_type":"text",
								"title":"🔎 Nouvelle recherche",
								"payload":"MAIN_MENU"
							}
						]
					}

					fbsend.sendMessage(self._user.psid,resp)


				self.save({"question_processing":None})	
				return True


			elif payload == "SHOW_LOCALITIES":
				intent.append({"confidence":1,"value":"getServiceLocations"})
				self.save({"question_processing":None})


			elif payload == "ASK_ZONE_1":
				intent.append({"confidence":1,"value":"getServiceLocations"})
				message["nlp"]["entities"]["zoneName"] = [{"confidence":1,"value":"abidjan"}]
				self.currentZone = 1
				self._user.currentZone = 1
				self.currentLocation = None
				self._user.currentLocation = None
				self.save({
					"currentZone":1,
					"currentLocation":None,
					"question_processing":None
				})

			elif payload == "ASK_ZONE_2":
				intent.append({"confidence":1,"value":"getServiceLocations"})
				message["nlp"]["entities"]["zoneName"] = [{"confidence":1,"value":"interieur"}]
				self.currentZone = 2
				self._user.currentZone = 2
				self.currentLocation = None
				self._user.currentLocation = None
				self.save({
					"currentZone":2,
					"currentLocation":None,
					"question_processing":None
				})

			elif payload == "SELECT_MY_LOCALITY":

				intent.append({"confidence":1,"value":"getPharmaGarde"})

				if self._user.currentLocation is not None:
					item = {"confidence":1,"value":self._user.currentLocation}
					if self.currentLocationType == "quartier":
						message["nlp"]["entities"]["quartier"] = [item]
					else:
						message["nlp"]["entities"]["Commune"] = [item]

				m = [
					'Tu as selectionné la localité "{}"'.format(self._user.currentLocation),
					'Ta localité est "{}"'.format(self._user.currentLocation),
					'Tu as choisi de voir les gardes de "{}"'.format(self._user.currentLocation),
					'Je vais afficher les gardes de "{}"'.format(self._user.currentLocation)
				]
				resp:dict = {
					"text":random.choice(m)
				}
				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":None
				})

			elif payload == "ASK_PHARMACY_DETAILS":
				text = "Veux-tu maintenant afficher la situation géographique de l'une de ces pharmacies ?"

				if "insta" in message and message["insta"] == 2:
					text = "Veux-tu afficher la situation géographique de l'une de ces pharmacies ?"
		
				resp:dict = {
					"text":text,
					"quick_replies":[
						{
							"content_type":"text",
							"title":"✔ Oui",
							"payload":"SHOW_PHCIE_LOC"
						},
						{
							"content_type":"text",
							"title":"✖ Non",
							"payload":"ASK_PHARMACY_DETAILS_REFUSE"
						},
						# {
						# 	"content_type":"text",
						# 	"title":"🏅 Note moi !",
						# 	"payload":"RATE_CHATBOT"
						# }
					]
				}

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":"ASK_PHARMACY_DETAILS",
				})

				return True



			elif payload == "ASK_PHARMACY_DETAILS_REFUSE":
				"""
				l'utilisateur a refusé de voir la situation géographique des pharmacies afficher.
				il faut lui proposer de noter l'application
				"""
				resp:dict = {
					"text":"Tres bien",
					"quick_replies":[
						{
							"content_type":"text",
							"title":"🏅 Note moi !",
							"payload":"RATE_CHATBOT"
						},
						{
							"content_type":"text",
							"title":"🔎 Menu principal",
							"payload":"MAIN_MENU"
						}
					]
				}

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":None,
				})

				return True

			elif payload == "RATE_CHATBOT":
				"""
				l'utilisateur veux noter le chatbot
				"""

				if self.rate is None:
					m = [
						"{} pour m'ameliorer, j'ai besoin d'avoir ton feedback sur mes services ☺".format(self._user.first_name),
						"Stp {} Je veux ton feedback sur mes services ☺".format(self._user.first_name),
					]
					resp:dict = {
						"text":random.choice(m)
					}

					fbsend.sendMessage(self._user.psid,resp)

					

				m = [
					"Sur 5 points combien pourrais-tu m'attribuer ?",
				]

				replies = [
					{
						"content_type":"text",
						"title":"1️⃣",
						"payload":"RATE_CHATBOT_1"
					},
					{
						"content_type":"text",
						"title":"2️⃣",
						"payload":"RATE_CHATBOT_2"
					}
					,
					{
						"content_type":"text",
						"title":"3️⃣",
						"payload":"RATE_CHATBOT_3"
					},
					{
						"content_type":"text",
						"title":"4️⃣",
						"payload":"RATE_CHATBOT_4"
					},
					{
						"content_type":"text",
						"title":"5️⃣",
						"payload":"RATE_CHATBOT_5"
					}
				]

				if "origin" in message:
					if message["origin"] == "pharmacy_list":
						for i,v in enumerate(replies):
							replies[i]["payload"] = "_{}_".format(replies[i]["payload"])

				resp:dict = {
					"text":random.choice(m),
					"quick_replies":replies
				}

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":"RATE_CHATBOT",
				})

				return True

			elif payload.startswith("RATE_CHATBOT_") or payload.startswith("_RATE_CHATBOT_"):
				"""
				l'utilisateur vient d'attribuer une note au chatbot
				"""

				origin_paylaod = payload

				payload = payload.strip("_")
				rate = int(payload[-1])

				
				if payload == "RATE_CHATBOT_4":
					
					resp:dict = {
						"text":"Je suis enjaillé 😍"
					}
					fbsend.sendMessage(self._user.psid,resp)

					resp:dict = {
						"attachment": {
			            	"type": "image",
			                "payload": {
			                    "attachment_id": random.choice(GIPHY.HAPPY+GIPHY.SUCCESS),
			                }
						}
					}
					fbsend.sendMessage(self._user.psid,resp)

				elif payload == "RATE_CHATBOT_5":
					
					resp:dict = {
						"text":"Je suis mal enjaillé 😍"
					}
					fbsend.sendMessage(self._user.psid,resp)

					resp:dict = {
						"attachment": {
			            	"type": "image",
			                "payload": {
			                    "attachment_id": random.choice(GIPHY.HAPPY+GIPHY.SUCCESS),
			                }
						}
					}
					fbsend.sendMessage(self._user.psid,resp)

				elif rate < 3 :
					
					resp:dict = {
						"text":"Tchieuux tu n'as pas sciencé pour moi hein 😭"
					}
					fbsend.sendMessage(self._user.psid,resp)

					resp:dict = {
						"attachment": {
			            	"type": "image",
			                "payload": {
			                    "attachment_id": random.choice(GIPHY.SAD),
			                }
						}
					}
					fbsend.sendMessage(self._user.psid,resp)

					resp:dict = {
						"text":"pas grave je vais bosser dur et m'ameliorer 😜 💪"
					}
					fbsend.sendMessage(self._user.psid,resp)

				if origin_paylaod.startswith("_") and origin_paylaod.endswith("_"):

					resp:dict = {
						"text":"Merci {}".format(self._user.first_name),
					}
					fbsend.sendMessage(self._user.psid,resp)

					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"ASK_PHARMACY_DETAILS"
						},
						"insta":2
					}
					self.handle_quick_reply(m)
				else:
					resp:dict = {
						"text":"Merci {}".format(self._user.first_name),
						"quick_replies":[
							{
								"content_type":"text",
								"title":"🏅 Modifier la note",
								"payload":"RATE_CHATBOT"
							},
							{
								"content_type":"text",
								"title":"🔎 Menu principal",
								"payload":"MAIN_MENU"
							}
						]
					}
					fbsend.sendMessage(self._user.psid,resp)
					self.save({
						"question_processing":None,
					})

				rate = int(payload[-1])
				self.save({"rate":rate})
				

				return True
			elif payload == "SHOW_PHCIE_LOC":
				"""
				l'utilisateur dit vouloir afficher la situation géographique d'une 
				pharmacie
				"""
				m = [
					"Selectionne la pharmacie dans la liste proposée ci-dessous stp 🚶‍♂️",
					"Indique moi la pharmacie dans la liste proposée ci-dessous stp 🚶‍♂️",
					"Indique stp la pharmacie 😉",
					"Selectionne stp la pharmacie 😎",
				]
				resp:dict = {
					"text":random.choice(m)
				}

				if self.oldDataSearch is not None:
					resp["quick_replies"] = []
					d = self.oldDataSearch["data"][:10]

					resp["quick_replies"] = [{"content_type":"text","title":i["name"].replace("Pharmacie","Phcie"),"payload":"SELECT_PHCIE_"+i["name"]} for i in d]

					offset = len(d)
					self.offsetDataSearch = offset
					self.save({"offsetDataSearch":offset})

					if len(self.oldDataSearch["data"]) > 10:
						resp["quick_replies"].append({
							"content_type":"text",
							"title":"Suivant ➡",
							"payload":"NEXT_PHCIE"
						})

					if self._user.currentPharmacie:
						resp["quick_replies"].insert(0,{
							"content_type":"text",
							"title":"📍 {}".format(self._user.currentPharmacie),
							"payload":"SELECT_PHCIE_"+self._user.currentPharmacie
						}) 

					
				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":"SHOW_PHCIE_LOC",
				})

				return True



			elif payload == "LOCALITY_ALERT_SUBSCRIPTION":
				"""
				l'utilisateur dit vouloir etre informé du prochain tour de garde
				"""
				m = [
					'Cliques sur <me prévenir> pour être informé du prochain tour de garde {} 😁 ?'.format(self._user.currentLocation.title())
				]

				resp:dict = {
					"text":random.choice(m),
				}

				fbsend.sendMessage(self._user.psid,resp)

				resp:dict = {
					"attachment": {
				    	"type":"template",
				      	"payload": {
				        	"template_type":"one_time_notif_req",
				        	"title":"Prochain tour de garde",
				        	"payload":"LOCALITY_ALERT_SUBSCRIPTION_ACCEPT"
				      }
				    }
				}
				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":"LOCALITY_ALERT_SUBSCRIPTION",
				})

				return True

			elif payload == "PHARMACY_ALERT_SUBSCRIPTION":

				m = [
					'Souhaites-tu être informé regulièrement des périodes de garde de la {} 😁 ?'.format(self._user.currentPharmacie.title()),
					"Tu sais je peux aussi t'informer regulièrement des périodes de garde de la {}\r\nCela t'intéresse 😁 ?".format(self._user.currentPharmacie.title()),
				]

				resp:dict = {
					"text":random.choice(m),
					"quick_replies":[
							{
								"content_type":"text",
								"title":"✔ Oui",
								"payload":"PHARMACY_ALERT_SUBSCRIPTION_ACCEPT"
							},
							{
								"content_type":"text",
								"title":"✖ Non",
								"payload":"PHARMACY_ALERT_SUBSCRIPTION_REFUSE"
							}
						]
				}

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":"PHARMACY_ALERT_SUBSCRIPTION",
				})

				return True

			elif payload == "PHARMACY_ALERT_SUBSCRIPTION_ACCEPT":
				# l'utilisateur a accepté
				# on enregistre son choix puis,
				# on continue la converstion pour lui demander
				# si il veut afficher une autre pharmacie

				isExists = False

				if self._user.preferred_pharmacies:
					for i,v in enumerate(self._user.preferred_pharmacies):
						if v["name"].lower() == self._user.currentPharmacie.lower() and v["locality"].lower() == self._user.currentLocation.lower():
							isExists = True

							if v["subscribed"] == False:
								v["subscribed"] = True
								self._user.preferred_pharmacies[i]["subscribed"] = True

								db.user.update_one({
									"_id":self._user._id,
								},{
									"$set":self._user.preferred_pharmacies
								})
								break

				if isExists == False:
					db.user.update_one({
						"_id":self._user._id,
					},{
						"$push":{
							"preferred_pharmacies":{
								"name":self._user.currentPharmacie.lower(),
								"locality":self._user.currentLocation.lower(),
								"subscribed":True,
								"create_at":datetime.datetime.utcnow()
							}
						}
					})

				# on envoi un message de succès
				m = [
					"C'est bien noté tu recevras regulièrement les alertes de la {} 😉".format(self._user.currentPharmacie.title()),
					"Tu recevras desormais regulièrement les alertes de la {} 😉".format(self._user.currentPharmacie.title()),
				]

				resp:dict = {
					"text":random.choice(m),
				}
				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":None
				})

				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"ASK_PHARMACY_DETAILS"
					},
					"insta":2
				}

				return self.handle_quick_reply(m)

				

			elif payload in ["PHARMACY_ALERT_SUBSCRIPTION_REFUSE","LOCALITY_ALERT_SUBSCRIPTION_REFUSE"]:
				# l'utilisateur a refusé
				# on continue la converstion pour lui demander
				# si il veut afficher une autre pharmacie
				# 
				
				self.save({
					"question_processing":None
				})

				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"ASK_PHARMACY_DETAILS"
					},
					"insta":2
				}

				return self.handle_quick_reply(m)


			elif payload == "LOCALITY_ALERT_SUBSCRIPTION_ACCEPT":
				# l'utilisateur a accepté
				# on enregistre son choix puis,
				# on continue la converstion pour lui demander
				# si il veut afficher une autre pharmacie

				isExists = False
				one_time_notif_token = message["quick_reply"]["one_time_notif_token"]

				self.save({
					"pharmacy_one_time_notif_token":{
						"locality":self._user.currentLocation.lower(),
						"value":one_time_notif_token,
						"used":False
					}
				})

				# if self._user.preferred_localities:
				# 	for i,v in enumerate(self._user.preferred_localities):
				# 		if v["name"].lower() == self._user.currentLocation.lower():
				# 			isExists = True

				# 			if v["subscribed"] == False:
				# 				v["subscribed"] = True
				# 				self._user.preferred_localities[i]["subscribed"] = True

				# 				db.user.update_one({
				# 					"_id":self._user._id,
				# 				},{
				# 					"$set":self._user.preferred_localities
				# 				})
				# 				break

				# if isExists == False:
				# 	one_time_notif_token = message["quick_reply"]["one_time_notif_token"]

				# 	db.user.update_one({
				# 		"_id":self._user._id,
				# 	},{
				# 		"$push":{
				# 			"preferred_localities":{
				# 				"name":self._user.currentLocation.lower(),
				# 				"one_time_notif_token":one_time_notif_token,
				# 				"subscribed":True,
				# 				"create_at":datetime.datetime.utcnow()
				# 			}
				# 		}
				# 	})

				# on envoi un message de succès
				resp:dict = {
					"text":"C'est bien noté tu recevras le prochain le tour de garde {} 😉".format(self._user.currentLocation.title()),
				}

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":None,
				})

				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"ASK_PHARMACY_DETAILS"
					},
					"insta":2
				}


				return self.handle_quick_reply(m)


			elif payload == "MAIN_MENU": 
				# le visiteur demande a revenir au menu principal
				self._user.currentLocation = None
				self.currentLocation = None
				self.save({"currentLocation":None})

				if "insta" not in message:
					m = [
						"Tu as demandé le menu principal, et bien nous y sommes",
					]
					resp:dict = {
						"text":random.choice(m),
					}
					fbsend.sendMessage(self._user.psid,resp)


				m = [
					"Merci de selectionner un element du menu",
					"Selectionne le menu qui t'interesse",
					"Indique le menu qui t'interesse stp"
				]
				resp:dict = {
					"text":random.choice(m),
					"quick_replies":[
						{
							"content_type":"text",
							"title":"Pharmacie de garde",
							"payload":"GARDE_PHARMACY"
						},
						{
							"content_type":"text",
							"title":"🇨🇮 Covid19 Stats",
							"payload":"COVID19_STATS"
						},

						{
							"content_type":"text",
							"title":"📊 Sondages",
							"payload":"SURVEY_LIST"
						},
						{
							"content_type":"text",
							"title":"🏆 Quizz",
							"payload":"QUIZZ_LIST"
						}
					]
				}

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":"MAIN_MENU",
				})

				return True

			elif payload == "GARDE_PHARMACY": 
				# activation du menu pharmacie de garde
				
				m = [
					"Peux-tu selectionner la zone qui t'interesse",
					"Peux-tu m'indiquer la zone de ton choix ?",
					"Indique une nouvelle zone stp"
				]
				resp:dict = {
					"text":random.choice(m),
					"quick_replies":[
						{
							"content_type":"text",
							"title":"Abidjan",
							"payload":"ASK_ZONE_1"
						},
						{
							"content_type":"text",
							"title":"Intérieur du pays",
							"payload":"ASK_ZONE_2"
						},
						{
							"content_type":"text",
							"title":"Comment ça marche ❓",
							"payload":"HOW_IT_WORKS"
						}
					]
				}

				if self._user.currentZone:
					if self._user.currentZone == 1:
						title = resp["quick_replies"][0]["title"]
						resp["quick_replies"][0]["title"] = "📍 {}".format(title)
					else:
						title = resp["quick_replies"][1]["title"]
						resp["quick_replies"][1]["title"] = "📍 {}".format(title)


				self.save({
					"question_processing":"GARDE_PHARMACY",
				})

				fbsend.sendMessage(self._user.psid,resp)
				return True

			elif payload == "NEW_SEARCH": 
				# le visiteur demande une nouvelle recherche

				if self.oldDataLocations:
					# on envoi la liste preengistrée
					text = "\r\n".join(["▪ {}".format(i) for i in self.oldDataLocations])

					resp:dict = {
						"text":text
					}
					fbsend.sendMessage(self._user.psid,resp)


				m = [
					"Peux-tu indiquer la localité qui t'interesse ?",
					"Peux-tu indiquer la localité de ton choix ?",
					"Indique une nouvelle localité stp"
				]
				resp:dict = {
					"text":random.choice(m),
				}

				if self.oldDataLocations:
					d = self.oldDataLocations[:10]

					resp["quick_replies"] = [{"content_type":"text","title":i,"payload":"SELECT_LOCALITY_"+i} for i in d]

					offset = len(d)
					self.offsetDataLocations = offset
					self.save({"offsetDataLocations":offset})

					resp["quick_replies"].append({
						"content_type":"text",
						"title":"Suivant ➡",
						"payload":"NEXT_LOCALITIES"
					})


				if self._user.currentLocation:
					if "quick_replies" not in resp:
						resp["quick_replies"] = []

					resp["quick_replies"].insert(0,{
						"content_type":"text",
						"title":"📍 {}".format(self._user.currentLocation),
						"payload":"SELECT_MY_LOCALITY"
					})

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":"NEW_SEARCH",
				})

				return True

			elif payload == "SHARE_BOT": 
				# le visiteur demande une nouvelle recherche
				m = [
					"Quel honneur 😜 ! c'est genial ! 🔥🔥",
					"C'est vraiment un honneur 💕",
					"Tout l'honneur est pour moi 💕  ! c'est genial ! 🔥🔥",
				]
				resp:dict = {
					"text":random.choice(m)
				}
				ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
				self.addItem(ctx)
				fbsend.sendMessage(self._user.psid,resp)

				resp:dict = {
					"text": "https://m.me/CiPharmaBot"
				}

				resp:dict = {
					"attachment":{
						"type":"template",
						"payload": {
							"template_type":"generic",
							"elements": [
							    {
							    	"title": "Pharma Garde",
							  		"subtitle":"Chatbot qui t'aide à trouver une pharmacie de garde dans la localité de ton choix",
							  		"image_url":"https://cipharmabot.herokuapp.com/static/logo-512x512.png",
							    	"buttons":[
							    		{
								            "type":"web_url",
								            "title":"Ouvrir",
								            "url":"https://m.me/CiPharmaBot",
								        }
							    	],
							    	"default_action": {
								        "type": "web_url",
								        "url": "https://m.me/CiPharmaBot",
								        "messenger_extensions": False,
								        "webview_height_ratio": "tall"
								    },
							    }
							]
						}
					}
				}

				fbsend.sendMessage(self._user.psid,resp)
				ctx = ContextMessage(message=resp,code=ContextCode.SHARE)
				self.addItem(ctx)

				m = [
					"N'hésites pas à relancer une recherche si tu en as besoin 😜",
					"N'hésites surtout pas à relancer une recherche 😜",
				]
				resp:dict = {
					"text":random.choice(m),
					"quick_replies":[
						{
							"content_type":"text",
							"title":"🔎 Menu principal",
							"payload":"MAIN_MENU"
						}
					]
				}
				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":None,
				})

				return True

			elif payload in ["NEXT_LOCALITIES","PREV_LOCALITIES"]:
				offset = self.offsetDataLocations
				rest = []

				if payload == "PREV_LOCALITIES":
					mod = offset % 10
					offset = offset - mod - 10

				rest = self.oldDataLocations[offset:offset+10]
				rest_len = len(rest)
				new_offset = offset + rest_len

				if len(rest) == 0:
					return True

				if payload == "PREV_LOCALITIES":
					if offset > 0:
						new_offset = offset


				self.offsetDataLocations = new_offset
				self.save({"offsetDataLocations":new_offset})
				
				m = [
					"Quelle est ta localité pour que j'affiche les pharmacies de garde 🔥",
					"Quelle localité choisis-tu pour que j'affiche les pharmacies de garde 🔥",
					"Peux-tu saisir ta localité pour que j'affiche les pharmacies de garde 🔥",
					"Peux-tu saisir ta localité, pour que j'affiche les pharmacies de garde 🔥",
				]
				resp:dict = {
					"text":random.choice(m),
					"quick_replies":[{"content_type":"text","title":i,"payload":"SELECT_LOCALITY_"+i} for i in rest]
				}



				if offset - 10 >= 0:
					resp["quick_replies"].insert(0,{
						"content_type":"text",
						"title":"⬅ Precedent",
						"payload":"PREV_LOCALITIES"
					})


				if new_offset < len(self.oldDataLocations):
					# il en reste encore
					resp["quick_replies"].append({
						"content_type":"text",
						"title":"Suivant ➡",
						"payload":"NEXT_LOCALITIES"
					})

				if self._user.currentLocation:
					resp["quick_replies"].insert(0,{
						"content_type":"text",
						"title":"📍 {}".format(self._user.currentLocation),
						"payload":"SELECT_MY_LOCALITY"
					}) 

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":"SHOW_LOCALITIES",
				})

				return True

			elif payload in ["NEXT_PHCIE","PREV_PHCIE"]:
				offset = self.offsetDataSearch
				rest = []

				if payload == "PREV_PHCIE":
					mod = offset % 10
					offset = offset - mod - 10

				rest = self.oldDataSearch["data"][offset:offset+10]
				rest_len = len(rest)
				new_offset = offset + rest_len

				if len(rest) == 0:
					return True

				if payload == "PREV_PHCIE":
					if offset > 0:
						new_offset = offset


				self.offsetDataSearch = new_offset
				self.save({"offsetDataSearch":new_offset})
				
				m = [
					"Veux-tu afficher la situation géographique de l'une de ces pharmacies ?",
					"Situation géographique de l'une de ces pharmacies ?",
				]
				resp:dict = {
					"text":random.choice(m),
					"quick_replies":[{"content_type":"text","title":i["name"].replace("Pharmacie","Phcie"),"payload":"SELECT_PHCIE_"+i["name"]} for i in rest]
				}


				if offset - 10 >= 0:
					resp["quick_replies"].insert(0,{
						"content_type":"text",
						"title":"⬅ Precedent",
						"payload":"PREV_PHCIE"
					})


				if new_offset < len(self.oldDataSearch["data"]):
					# il en reste encore
					resp["quick_replies"].append({
						"content_type":"text",
						"title":"Suivant ➡",
						"payload":"NEXT_PHCIE"
					})


				if self._user.currentPharmacie:
					resp["quick_replies"].insert(0,{
						"content_type":"text",
						"title":"📍 {}".format(self._user.currentPharmacie),
						"payload":"SELECT_PHCIE_"+self._user.currentPharmacie
					})

				fbsend.sendMessage(self._user.psid,resp)

				self.save({
					"question_processing":"ASK_PHARMACY_DETAILS",
				})

				return True
			
			elif payload.startswith("VIEW_ALERT_"):

				r = re.search(r"VIEW_ALERT_(.+)",payload)
				locality = r.group(1)
				intent.append({"confidence":1,"value":"getPharmaGarde"})
				item = {"confidence":1,"value":locality}
				message["nlp"]["entities"]["quartier"] = [item]

				self.save({
					"question_processing":None,
				})
				
			else:
				r = re.search(r"SELECT_PHCIE_(.+)",payload)
				if r is not None:
					# on selection une pharmacie
					
					intent.append({
						"confidence":1,
						"value":"getPharmaGarde"
					})
					
					item = {
						"confidence":1,
						"value":r.group(1)
					}
					message["nlp"]["entities"]["pharmaName"] = [item]

					self.save({
						"question_processing":None,
					})
				
				else:
					r = re.search(r"SELECT_LOCALITY_(.+)",payload)
					if r is not None:
						
						intent.append({
							"confidence":1,
							"value":"getPharmaGarde"
						})
						
						item = {
							"confidence":1,
							"value":r.group(1)
						}

						message["nlp"]["entities"]["Commune"] = [item]

						self.save({
							"question_processing":None,
						})

			message["nlp"]["entities"]["intent"] = intent
		else:
			# on va gerer des messages qui se rapproche des quick_replies
			if "nlp" not in message:
				return

			if "entities" not in message["nlp"]:
				return

			if "intent" not in  message["nlp"]["entities"]:
				return

			intent = message["nlp"]["entities"]["intent"][0]

			if intent["value"] == "refuse":
				# lorsqu'un utilisateur ecrit juste "non"
				# il faut cherche la question a laquelle se rapport cette reponse  
				
				if self._user.question_processing in ["PHARMACY_ALERT_SUBSCRIPTION","LOCALITY_ALERT_SUBSCRIPTION"]:
					
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"PHARMACY_ALERT_SUBSCRIPTION_REFUSE"
						}
					}
					return self.handle_quick_reply(m)

			elif intent["value"] == "accept":
				# lorsqu'un utilisateur ecrit juste "oui"
				# il faut cherche la question a laquelle se rapport
				# cette reponse
				# 
				

				if self._user.question_processing == "ASK_PHARMACY_DETAILS":
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"SHOW_PHCIE_LOC"
						}
					}
					return self.handle_quick_reply(m)

				elif self._user.question_processing == "PHARMACY_ALERT_SUBSCRIPTION":

					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"PHARMACY_ALERT_SUBSCRIPTION_ACCEPT"
						}
					}
					return self.handle_quick_reply(m)

				elif self._user.question_processing == "LOCALITY_ALERT_SUBSCRIPTION":
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"LOCALITY_ALERT_SUBSCRIPTION_ACCEPT"
						}
					}
					return self.handle_quick_reply(m)

							

	def check_if_user_subscribe_to_current_pharmacy_alert(self):
		isSubscribed = False
		if self._user.preferred_pharmacies:
			for i,v in enumerate(self._user.preferred_pharmacies):
				if v["name"].lower() == self._user.currentPharmacie.lower() and v["locality"].lower() == self._user.currentLocation.lower():
					isSubscribed = True
					break

		return isSubscribed

	def check_if_user_subscribe_to_current_locality_alert(self):
		isSubscribed = False
		if self._user.preferred_localities:
			for i,v in enumerate(self._user.preferred_localities):
				if v["name"].lower() == self._user.currentLocation.lower():
					isSubscribed = True
					break

		return isSubscribed


	def load_covid19_stats(self,url):
		"""
		l'utilisateur veut voir les stitistiques du coronavirus
		"""


		result = {"cases":0,"deaths":0,"recovered":0}
		r = requests.get(url)
		if r.status_code == 200:
			html = str(r.text)

			html = BeautifulSoup(html,"lxml")
			container = html.find_all(id="maincounter-wrap")

			for i,el in enumerate(container):
				h1 = el.find("h1")
				counter = el.select(".maincounter-number span")[0]
				if i == 0:
					key = "cases"
				elif i == 1:
					key = "deaths"
				elif i == 2:
					key = "recovered"

				result[key] = counter.string.replace(","," ")

		return result

	def saveGardePeriodView(self):
		"""
		pour enregistrer les vues pour une periode de garde
		"""
		garde_period = db.garde_period.find_one({"is_active":True})
		db.garde_period_view.insert_one({
			"garde_period_id":garde_period["_id"],
			"user_id":self._user._id,
			"create_at":datetime.datetime.utcnow()
		})

	def saveUserSearch(self,mode:str=None):

		if self._user.currentZone and self._user.currentLocation:
			obj = {
				"user_id":self._user._id,
				"zone":self._user.currentZone,
				"locality":self._user.currentLocation.lower(),
				"create_at":datetime.datetime.utcnow()
			}

			if mode == "pharmacy":
				obj["pharmacy"] = self._user.currentPharmacie.lower()

			db.user_search.insert_one(obj)


	def process(self,args=None):
		fbsend = FBSend()
		processed = False

		




