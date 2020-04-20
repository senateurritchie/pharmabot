#!/usr/bin/python3

import pymongo
from bson.objectid import ObjectId
from slugify import slugify
import os
import requests
import datetime
from .EventDispatcher import EventDispatcher


DATABASE_URL = os.environ["DATABASE_URL"]
client = pymongo.MongoClient(DATABASE_URL)
db = client.pharma_garde

class ContextUser(EventDispatcher):

	def __init__(self,user_id,first_name=None,last_name=None,locale=None,gender=None,profile_pic=None):
		super().__init__()

		self._id = None
		self.psid = user_id
		self.first_name = first_name
		self.last_name = last_name 
		self.locale = locale
		self.gender = gender
		self.profile_pic = profile_pic

		# permet de savoir si une question obligatoire est posée
		# la valeur en quick_reply de cette question y est stockée
		self.question_processing = None
		self.last_survey_id = None
		self.last_survey_offset = 0
		self.last_quizz_id = None
		self.last_quizz_offset = 0


		# pour enregistrer la localité du visiteur
		self.currentLocation = None
		# la pharmacie recherchee pr le visiteur
		self.currentPharmacie = None
		# la zone de recherche soit 1 = Abidjan, 2 = Interieur du pays
		self.currentZone = None
		self.last_presence = None
		self.preferred_pharmacies = None
		self.preferred_localities = None
		self.rate = None
		self.in_consulting = False
		self.one_time_notif_token = None
		

	
	def hydrate(self,payload):
		for key,val in payload.items():
			if not key.startswith("__") and key in self.__dict__:
				setattr(self,key,val)

	def update_from_fb(self):

		if self.first_name:
			return

		# on charge les informations du visiteur depuis facebook
		params = {
			"fields":"id,first_name,last_name,profile_pic",
			"access_token":os.environ['FB_PAGE_ACCESS_TOKEN']
		}
		url = "https://graph.facebook.com/v3.3/{}".format(self.psid)
		r = requests.get(url,params=params)
		if r.status_code == 200:
			rdata = r.json()
			self.first_name = rdata["first_name"]
			self.last_name = rdata["last_name"] 
			self.profile_pic = rdata["profile_pic"]

			if "locale" in rdata:
				self.locale = rdata["locale"]

			if "gender" in rdata:
				self.gender = rdata["gender"]

			db.user.update_one({
				"_id":self._id,
			},{
				"$set":{
					"first_name":self.first_name,
					"last_name":self.last_name,
					"locale":self.locale,
					"gender":self.gender,
					"profile_pic":self.profile_pic
				}
			})

	def load(self):
		if not self.psid:
			return

		user = db.user.find_one({
			"psid":self.psid
		})

		if user:
			self.hydrate(user)
		else:

			_id = db.user.insert_one({
				"psid":self.psid,
				"one_time_notif_token":None,
				"question_processing":None,
				"last_survey_id": None,
				"last_survey_offset":0,
				"last_quizz_id": None,
				"last_quizz_offset":0,
				"in_consulting":False,
				"first_name":None,
				"last_name":None,
				"locale":None,
				"gender":None,
				"profile_pic":None,
				"create_at":datetime.datetime.utcnow(),
				"last_presence":datetime.datetime.utcnow()
			}).inserted_id
			self._id = _id


		
		self.update_from_fb()

	def count_conversation(self):
		return db.conversation.find({"user_id":self._id}).count()

