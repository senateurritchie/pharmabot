#!/usr/bin/python3
# -*-coding:utf8 -*-

from enum import Enum
import datetime
import logging
import random
import pymongo

from .FBSend import FBSend

class ConsultationStatus(Enum):
	
	NONE = 0 		# rien
	ACCEPTED = 1 	# la consultation est acceptée par le medecin
	REFUSED = 2 	# la demande de consultation est refusée par le medecin
	NOT_AVAILABLE = 3 		# pas de disponibilité
	PENDING = 4 	# la demande de consultation est en attente d'acceptation
	FINISH = 5 		# la consultation est terminée
	AUTOCLOSE = 6


class Consultation:
	"""
	cette class permet d'etablir des conversations directes
	entre un usager de pharmabot et un medecin
	dûment inscrit sur la plateforme pharma garde
	"""

	def __init__(self, user_id=None,medecin_id=None,data:dict=None):
		self._id = None
		self.user_id = user_id # c'est le patient
		self.medecin_id = None # c'est le medecin commit à cette consultation
		self.refuse_ids = [] 
		self.messages = [] # les messages echangés entre le patient et le medecin
		self.state:ConsultationStatus = ConsultationStatus.NONE
		self.last_presence:datetime.datetime = None
		self.create_at:datetime.datetime = datetime.datetime.utcnow()
		self.accepted_at:datetime.datetime = None

		if data is not None:
			self.hydrate(data)

	def hydrate(self,data):
		"""
		hydrate l'objet Consultation avec les infos provenant
		de la base de données
		"""

		for i in data:
			if not i.startswith("__") and i in self.__dict__:
				value = data[i]
				if i == "state":
					value = ConsultationStatus(value)
				setattr(self,i,value)




	def retrieve_patient(self):
		"""
		charge les info du patient depuis la base de données
		"""
		client = pymongo.MongoClient()
		db = client.pharma_garde

		d = db.user.find_one({
			"_id":self.user_id
		})
		return d

	def retrieve_medecin(self):
		"""
		charge les infos du medecin depuis la base de données
		"""
		client = pymongo.MongoClient()
		db = client.pharma_garde

		d = db.medecin.aggregate([
			{
				"$match":{
					"_id":self.medecin_id
				}
			},
			{
				"$lookup":{
					"from":"user",
					"localField":"user_id",
					"foreignField":"_id",
					"as":"user",
				}
			},
			{"$limit":1}
		])

		d = [i for i in d]

		if len(d) == 0:
			raise Exception("Le medecin id: {} n'existe pas dans la base de données".format(str(self.medecin_id)))

		medecin = d[0]
		medecin["user"] = medecin["user"][0]
		return medecin

	def get_available_medecins(self):
		"""
		selectionne un medecin disponible pour une consultation
		"""
		client = pymongo.MongoClient()
		db = client.pharma_garde

		medecins = db.medecin.aggregate([

			
			{"$lookup":{
				"from":"user",
				"localField":"user_id",
				"foreignField":"_id",
				"as":"user"
			}},
			{"$match":{
				"user.in_consulting":False,
				"user._id":{"$ne":self.user_id},
				"_id":{"$nin":self.refuse_ids}
			}},

			{
				"$addFields":{
					"user":{"$arrayElemAt":["$user",0]}
				}
			}
		])

		logging.info("Selection de medecin disponible pour la demande de consultation N° {}".format(str(self._id)))

		medecins = [i for i in medecins]

		
		if len(medecins) == 0:
			return

		medecin = random.choice(medecins)
		user = db.user.find_one({"_id":medecin["user_id"]})
		medecin["user"] = user
		user_name = user["first_name"] + " " + user["last_name"]
		medecin_id = medecin["_id"]
		
		logging.info("choix du medecin {} id: {} pour la demande de consultation N° {}".format(user_name,str(medecin_id),str(self._id)))

		return medecin

	def save(self):
		"""
		enregistre les données de l'objet consultation dans la base de données
		"""

		client = pymongo.MongoClient()
		db = client.pharma_garde

		inspect = dir(self)
		data = {}
		for i in inspect:
			if not i.startswith("__") and i in self.__dict__:
				data[i] = getattr(self,i)
				if isinstance(data[i],Enum):
					data[i] = data[i].value



		if len(data):
			if self._id is None:
				del data["_id"]
				self._id = db.consultation.insert_one(data).inserted_id
				logging.info("Création de la demande de consultation N° {}".format(str(self._id)))
			else:
				db.consultation.update_one({
					"_id":self._id
				},{
					"$set":data
				})
				logging.info("Mise à jour de la demande de consultation N° {}".format(str(self._id)))




	def run(self,options:dict={}):
		"""
		demarre le processus d'une demande de consultation
		1. 	verifier que le demandeur n'a pas deja une
			demande en cours

		2. 	si il n'y a pas de medecin disponible
			on informe le demandeur

			si un medecin est disponible on lui envoi
			une invitation à rejoindre cette demande
		"""
		client = pymongo.MongoClient()
		db = client.pharma_garde
		
		fbsend:FBSend = FBSend()
		user = self.retrieve_patient()

		if user["in_consulting"]:
			resp:dict = {
				"text":'{} tu es déja avec un medecin en consultation\r\nMerci de mettre fin à cette session avant d\'ouvrir une autre."'.format(user["first_name"]),
				"quick_replies":[
					{
						"content_type":"text",
						"title":"⌛ Arreter",
						"payload":"CONSULTATION_CLOSE_{}".format(str(self._id))
					}
				]
				

			}
			fbsend.sendMessage(user["psid"],resp)
			return

		pending_action = db.consultation.find_one({
			"user_id":self.user_id,
			"state":{"$in":[1,4]}
		})

		if pending_action:

			if pending_action["state"] == 1:
				pass
			elif pending_action["state"] == 4:
				resp:dict = {
					"text":'{} merci de patienter un medecin sera affecté à ta demande dans un instant.'.format(user["first_name"])
				}
				fbsend.sendMessage(user["psid"],resp)

			return



		if self.state != ConsultationStatus.NONE:
			return


		medecin = self.get_available_medecins()
		if medecin is None:

			self.state = ConsultationStatus.NOT_AVAILABLE
			self.save()

			if "from" not in options:
				# envoyer un message au patient
				resp:dict = {
					"text":"Consultation N° {}".format(str(self._id)[16:].upper())
				}
				fbsend.sendMessage(user["psid"],resp)

			resp:dict = {
				"text":"{}, pour l'heure, nos consultants sont tous en ligne. merci de réessayer ulterieurement 😞".format(user["first_name"]),

				"quick_replies":[
					{
						"content_type":"text",
						"title":"F.A.Q 📖",
						"payload":"ABOUT_US_FAQ"
					},
					{
						"content_type":"text",
						"title":"Tour de garde 🔎",
						"payload":"MAIN_MENU"
					}
				]
			}
			fbsend.sendMessage(user["psid"],resp)

			return

		
		self.state = ConsultationStatus.PENDING
		self.medecin_id = medecin["_id"]
		self.last_presence = datetime.datetime.utcnow()
		self.save()

		resp:dict = {
			"text":"Consultation N° {}".format(str(self._id)[16:].upper())
		}
		fbsend.sendMessage(user["psid"],resp)
		
		resp:dict = {
			"text":"Merci de patienter un medecin sera avec toi dans quelques instants"
		}
		fbsend.sendMessage(user["psid"],resp)

		


		resp:dict = {
			"text":"Consultation N° {}".format(str(self._id)[16:].upper())
		}
		fbsend.sendMessage(medecin["user"]["psid"],resp)


		greet = "Bonjour" if self.create_at.hour < 14 else "Bonsoir"
		resp:dict = {
			"text":"Dr. {} {}, une nouvelle consultation pour vous\r\nl'acceptez-vous ?".format(medecin["user"]["first_name"],greet,str(self._id).upper()),
			"quick_replies":[{
					"content_type":"text",
					"title":"Oui",
					"payload":"CONSULTATION_ACCEPTED_{}".format(str(self._id))
				},
				{
					"content_type":"text",
					"title":"Non",
					"payload":"CONSULTATION_REFUSED_{}".format(str(self._id))
				}
			]
		}

		fbsend.sendMessage(medecin["user"]["psid"],resp)
		logging.info("Envoi de la demande de consultation N° {} pour acceptation au medecin id: {}".format(str(self._id),str(medecin["_id"])))


	def accept(self):
		"""
		action pour accepter une demande de consultation
		"""
		client = pymongo.MongoClient()
		db = client.pharma_garde
		fbsend:FBSend = FBSend()

		if self.state != ConsultationStatus.PENDING:
			return

		self.state = ConsultationStatus.ACCEPTED
		self.save()

		medecin = self.retrieve_medecin()
		user = self.retrieve_patient()

		# on informe le patient de la disponibilité du medecin
		resp:dict = {
			"text":"Le medecin est maintenant à ton écoute explique lui tout",
		}
		fbsend.sendMessage(user["psid"],resp)


		resp:dict = {
			"text":'la seance sera fermée pour une periode d\'inactivité de 5 minutes'
		}
		fbsend.sendMessage(medecin["user"]["psid"],resp)
		fbsend.sendMessage(user["psid"],resp)


		db.user.update_many({
			"_id":{"$in":[self.user_id,medecin["user"]["_id"]]}
		},{
			"$set":{
				"in_consulting":True
			}
		})

		logging.info("Acceptation de la demande de consultation N° {}".format(str(self._id)))

	def refuse(self):
		"""
		action pour refuser une demande de consultation
		dans ce cas on recherche un autre medecin disponible
		pour cette consultation
		"""

		client = pymongo.MongoClient()
		db = client.pharma_garde
		fbsend:FBSend = FBSend()

		if self.state != ConsultationStatus.PENDING:
			return

		self.state = ConsultationStatus.NONE
		self.refuse_ids.append(self.medecin_id)
		self.save()


		medecin = self.retrieve_medecin()

		user_name = medecin["user"]["first_name"]+" "+medecin["user"]["last_name"]
		medecin_id = str(medecin["_id"])

		logging.info("Refus de la demande de consultation N° {} par le medecin {} id: {}".format(str(self._id),user_name,medecin_id))

		logging.info("recherche d'un autre medecin pour la demande de consultation N° {}".format(str(self._id)))

		resp:dict = {
			"text":"Bien noté Dr. {} merci pour l'intéret que vous portez à Pharmabot".format(medecin["user"]["first_name"])
		}
		fbsend.sendMessage(medecin["user"]["psid"],resp)

		self.run({"from":"refuse"})




	def finish(self):
		"""
		pour terminer une consultation
		"""

		fbsend:FBSend = FBSend()

		client = pymongo.MongoClient()
		db = client.pharma_garde

		if self.state != ConsultationStatus.ACCEPTED:
			return

		self.state = ConsultationStatus.FINISH
		self.save()

		medecin = self.retrieve_medecin()
		user = self.retrieve_patient()


		resp:dict = {
			"text": "consultation N° {} fermée".format(str(self._id)[16:].upper()),
			"quick_replies":[
				{
					"content_type":"text",
					"title":"Tour de garde 🔎",
					"payload":"MAIN_MENU"
				}
			]
		}
		fbsend.sendMessage(user["psid"],resp)

		resp:dict = {
			"text": "consultation N° {} fermée".format(str(self._id)[16:].upper())
		}
		fbsend.sendMessage(medecin["user"]["psid"],resp)


		db.user.update_many({
			"_id":{"$in":[self.user_id,medecin["user"]["_id"]]}
		},{
			"$set":{
				"in_consulting":False
			}
		})


	def close(self):
		"""
		action automatique du CRON pour fermer
		les consultation de plus de 5 miniutes d'inactivité
		"""
		client = pymongo.MongoClient()
		db = client.pharma_garde

		fbsend:FBSend = FBSend()

		oldState = self.state.name

		self.state = ConsultationStatus.AUTOCLOSE
		self.save()
		

		if oldState == 'PENDING':
			medecin = self.retrieve_medecin()

			self.refuse_ids.append(self.medecin_id)
			self.save()
			self.state = ConsultationStatus.NONE

			resp:dict = {
				"text": "vous avez été absent pour cette demande de consultation N° {} elle est donc fermée".format(str(self._id)[16:].upper())
			}
			fbsend.sendMessage(medecin["user"]["psid"],resp)

			self.run({"from":"timeout"})
			
		elif oldState == 'ACCEPTED':

			user = self.retrieve_patient()
			medecin = self.retrieve_medecin()

			resp:dict = {
				"text": "vous avez atteint la durée d'inactivité. la consultation N° {} est fermée".format(str(self._id)[16:].upper()),
				"quick_replies":[
					{
						"content_type":"text",
						"title":"Tours de gardes 🔎",
						"payload":"MAIN_MENU"
					}
				]
			}
			fbsend.sendMessage(user["psid"],resp)

			resp:dict = {
				"text": "vous avez atteint la durée d'inactivité. la consultation N° {} est fermée".format(str(self._id)[16:].upper())
			}
			fbsend.sendMessage(medecin["user"]["psid"],resp)


			db.user.update_many({
				"_id":{"$in":[self.user_id,medecin["user"]["_id"]]}
			},{
				"$set":{
					"in_consulting":False
				}
			})



	def addMessage(self,message:dict,how_talks=0):
		"""
		enregistre les messages de cette consultation

		message = {
			"sender_id":None,
			"text":None,
			"attachments":None,
			"create_at":datetime.datetime.utcnow()
		}
		"""
		fbsend:FBSend = FBSend()

		client = pymongo.MongoClient()
		db = client.pharma_garde

		message["create_at"] = datetime.datetime.utcnow()

		self.last_presence = datetime.datetime.utcnow()

		has_attachments = True if "attachments" in message else False

		text = ""

		if "text" in message:
			text = message["text"]

		tpl = {
			"sender_id":self.user_id,
			"text":text,
			"attachments":None,
			"create_at":datetime.datetime.utcnow(),
		}

		medecin = self.retrieve_medecin()
		user = self.retrieve_patient()

		if how_talks == 0:
			"""
			le patient parle
			"""

			u_psid = medecin["user"]["psid"]
			

			if has_attachments:
				for i in message["attachments"]:

					resp:dict = {
						"attachment": i
					}
					fbsend.sendMessage(u_psid,resp)

			else:
				resp:dict = {
					"text": "⛑\r\n\r\n{}".format(message["text"]),
					"quick_replies":[
						{
							"content_type":"text",
							"title":"⌛ Arreter",
							"payload":"CONSULTATION_CLOSE_{}".format(str(self._id))
						}
					]
				}
				fbsend.sendMessage(u_psid,resp)

		else:
			"""
			le medecin parle
			"""
			tpl["sender_id"] = medecin["_id"]
			u_psid = user["psid"]
			

			if has_attachments:
				for i in message["attachments"]:
					resp:dict = {
						"attachment": i
					}
					fbsend.sendMessage(u_psid,resp)

			else:
				resp:dict = {
					"text": "⛑\r\n\r\n{}".format(message["text"]),
					"quick_replies":[
						{
							"content_type":"text",
							"title":"⌛ Arreter",
							"payload":"CONSULTATION_CLOSE_{}".format(str(self._id))
						}
					]
				}
				fbsend.sendMessage(u_psid,resp)

			

		self.messages.append(tpl)
		self.save()









		
