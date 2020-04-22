#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
from bs4 import BeautifulSoup
import requests
import re
import random
import time

from .OfficineUpdater import OfficineUpdater
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode,GIPHY

class PharmaGardeAnswer(Answer):
	"""
	pour les reponses demandant les pharmacies de garde
	"""
	def __init__(self):
		super().__init__(["getPharmaGarde"])
		self.scrappingUrl = "https://www.abidjan.net/inc/abidjan/inc_pharmacie.js"


	def process(self,e,options:dict=None) -> str:

		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)


		# on cherche les lieux
		communes:list = []
		quartiers:list = []
		pharmacies:list = []
		
		if "quartier" in e["entities"]:
			quartiers = [i["value"].strip().upper() for i in e["entities"]["quartier"] if i["confidence"] > 0.5 and "suggested" not in i]

		if "Commune" in e["entities"]:
			communes = [i["value"].strip().upper() for i in e["entities"]["Commune"] if i["confidence"] > 0.5 and "suggested" not in i]

		if "pharmaName" in e["entities"]:
			pharmacies = [i["value"] for i in e["entities"]["pharmaName"] if i["confidence"] > 0.5]


		answer:str = ""
		

		if len(quartiers) == 0 and len(communes) == 0 and len(pharmacies) == 0:

			m = [
				"pour gagner du temps 🏃‍♂️ indiques stp une localité que je couvre.",
				"si tu veux gagner du temps 🏃‍♂️ indiques stp une localité que je couvre",
				"🚶il est preferable de selectionner une localité que je couvre",
				"🚶 il est souhaitable de selectionner une localité que je couvre",
				"🚶 je pense que tu devrais indiquer une localité que je couvre "
			]
			resp:dict = {"text":random.choice(m)}
			self.fbsend.sendMessage(sender_psid,resp)

			# un git du style j'attend votre reponse
			resp:dict = {
				"attachment": {
	            	"type": "image",
	                "payload": {
	                    "attachment_id": random.choice(GIPHY.WAITING),
	                }
				}
			}
			self.fbsend.sendMessage(sender_psid,resp)

			manager.process()
		else:

			params:dict = {"quartier":quartiers,"commune":communes,"pharmacie":pharmacies}

			# on met a jour la localité demandée
			currentLocation =  None
			currentLocationType = None
			currentPharmacie = None
			if len(quartiers):
				currentLocation = quartiers[0]
				currentLocationType = "quartier"
				manager.currentLocation = currentLocation
				manager._user.currentLocation = currentLocation
				manager.currentLocationType = currentLocationType
				manager.save({"currentLocation":currentLocation,"currentLocationType":currentLocationType})
			elif len(communes):
				currentLocation = communes[0]
				currentLocationType = "commune"
				manager.currentLocation = currentLocation
				manager._user.currentLocation = currentLocation
				manager.currentLocationType = currentLocationType
				manager.save({"currentLocation":currentLocation,"currentLocationType":currentLocationType})

			if len(pharmacies):
				currentPharmacie = pharmacies[0]
				manager.currentPharmacie = currentPharmacie
				manager._user.currentPharmacie = currentPharmacie
				manager.save({"currentPharmacie":currentPharmacie})



			if len(pharmacies) == 0:
			
				text = 'Tu as dit "{}"'.format(currentLocation.title())
				if manager._user.currentZone:
					if manager._user.currentZone == 1:
						text = text + ", dans la zone d'abidjan"
					else:
						text = text + ", à l'intérieur du pays"

				resp:dict = {"text":text}
				ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
				manager.addItem(ctx)
				self.fbsend.sendMessage(sender_psid,resp)
			else:

				text = 'Tu as dit la "{}"'.format(currentPharmacie.title())

				if manager._user.currentLocation:
					text = text + ", à {}".format(manager._user.currentLocation.title())


				resp:dict = {"text":text}
				ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
				manager.addItem(ctx)
				self.fbsend.sendMessage(sender_psid,resp)


			m = [
				"un instant que je cherche un peu 🏃‍♂️",
				"je te reviens tres vite 🏃‍♂️",
				"laisses moi voir stp 🤨",
				"voyons voir ce que j'ai là 🤔",
			]
			resp:dict = {"text":random.choice(m)}
			ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
			manager.addItem(ctx)
			self.fbsend.sendMessage(sender_psid,resp)

			# un git du style j'y travail en ce moment
			resp:dict = {
				"attachment": {
	            	"type": "image",
	                "payload": {
	                    "attachment_id": random.choice(GIPHY.TYPING),
	                }
				}
			}
			self.fbsend.sendMessage(sender_psid,resp)
			#time.sleep(random.choice([2,3,1]))

			ofm = OfficineUpdater()
			r = ofm.search(**params)

			if len(r["data"]):

				manager.searchSuccess = manager.searchSuccess + 1
				manager.save({"searchSuccess":manager.searchSuccess})


				# on met a jour la question qui a appellé cette reponse
				args = {"answered":True,"required":False}
				manager.updateItem(ContextCode.ASK_LOCALITY,args)
				

				if len(pharmacies):
					# recherche d'une pharmacie specique
					item = r["data"][0]
					name = "{}".format(item['name'].replace("Phcie","Pharmacie"))
					if item['address']:
						text = "Tu peux joindre la {} au numéro suivant:\r\n{}".format(name,item['address'])
						resp:dict = {"text":text}
						self.fbsend.sendMessage(sender_psid,resp)

					if item['description']:
						text = "📍 situation géographique: {}".format(item['description'])
						resp:dict = {"text":text}
						self.fbsend.sendMessage(sender_psid,resp)


					# if manager.check_if_user_subscribe_to_current_pharmacy_alert() == False:	
					# 	m = {
					# 		"nlp":{},
					# 		"quick_reply":{
					# 			"payload":"PHARMACY_ALERT_SUBSCRIPTION"
					# 		},
					# 	}
					# 	manager.handle_quick_reply(m)
					# else:
					m = {
						"nlp":{},
						"quick_reply":{
							"payload":"ASK_PHARMACY_DETAILS"
						},
						"insta":2
					}
					manager.handle_quick_reply(m)

					manager.saveUserSearch("pharmacy")


				else:
					manager.oldDataSearch = r
					manager.save({"oldDataSearch":r})
					m = [
						"🗓 la periode en cours est",
						"🗓 la periode du tour de garde est"
					]
					prefix = random.choice(m)
					text =  prefix + " la " + r["period"].lower().capitalize()
					resp:dict = {"text":text}
					self.fbsend.sendMessage(sender_psid,resp)


					for item in r["data"]:
						text = "🏫 {}".format(item['name'].replace("Phcie","Pharmacie"))
						if item['address']:
							text = text + "\r\n{}".format(item['address'])

						if len(pharmacies):
							text = text + "\r\n\r\n{description}".format(description=item['description'])

						resp:dict = {"text":text}
						self.fbsend.sendMessage(sender_psid,resp)

					manager.saveUserSearch("normal")
					manager.saveGardePeriodView()


					if manager.check_if_user_subscribe_to_current_locality_alert() == False:

						m = {
							"nlp":{},
							"quick_reply":{
								"payload":"LOCALITY_ALERT_SUBSCRIPTION"
							},
						}
						manager.handle_quick_reply(m)
	
					else:
						m = {
							"nlp":{},
							"quick_reply":{
								"payload":"ASK_PHARMACY_DETAILS"
							},
							"insta":1
						}
						manager.handle_quick_reply(m)
				
			else:
				manager.searchFails = manager.searchFails + 1
				manager.save({"searchFails":manager.searchFails})

				if len(pharmacies):
					text = "Aïe.. il semble la {} n'est pas dans le tour des gardes cette semaine".format(pharmacies[0])
					resp:dict = {"text":text}
					self.fbsend.sendMessage(sender_psid,resp)

					

					
				m = {
					"nlp":{},
					"quick_reply":{
						"payload":"NEW_SEARCH"
					},
					"insta":2
				}
				manager.handle_quick_reply(m)
			
		return answer


