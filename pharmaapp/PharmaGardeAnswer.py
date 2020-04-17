#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
from bs4 import BeautifulSoup
import requests
import re
import random
import time

from .OfficineUpdater import OfficineUpdater
from .DefaultAnswer import DefaultAnswer
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
			ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
			manager.addItem(ctx)
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
				manager.saveUserActivity("PHARMA_TOUR_GARDE_ANSWER")
			
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
				manager.saveUserActivity("ONE_PHARMA_ANSWER")

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
				

				# m = [
				# 	"J'ai trouver  quelques chose pour toi 😜",
				# 	"j'espere ne pas avoir mis assez de temps 😋"
				# ]
				# resp:dict = {"text":random.choice(m)}
				# ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
				# manager.addItem(ctx)
				# self.fbsend.sendMessage(sender_psid,resp)

				if len(pharmacies):
					# recherche d'une pharmacie specique
					item = r["data"][0]
					name = "{}".format(item['name'].replace("Phcie","Pharmacie"))
					if item['address']:
						text = "Tu peux joindre la {} au numéro suivant:\r\n{}".format(name,item['address'])
						resp:dict = {"text":text}
						ctx = ContextMessage(message=resp,code=ContextCode.STREAMING_PHCIE)
						manager.addItem(ctx)
						self.fbsend.sendMessage(sender_psid,resp)

					if item['description']:
						text = "📍 situation géographique: {}".format(item['description'])
						resp:dict = {"text":text}
						ctx = ContextMessage(message=resp,code=ContextCode.STREAMING_PHCIE)
						manager.addItem(ctx)
						self.fbsend.sendMessage(sender_psid,resp)


					text = "Peux-tu stp, me suggerer une situation géographique encore plus precise de la {} ?😁".format(name)

					resp:dict = {
						"text":text,
						"quick_replies":[
							{
								"content_type":"text",
								"title":"✔ Oui",
								"payload":"SUGGEST_PHARMACY_LOC_TO_BOT"
							},
							{
								"content_type":"text",
								"title":"✖ Non",
								"payload":"REFUSE_PHARMACY_LOC_TO_BOT"
							}
						]
					}
					ctx = ContextMessage(message=resp,code=ContextCode.ASK_PHARMACY_LOC_TO_USER,answered=False)
					manager.addItem(ctx)
					self.fbsend.sendMessage(sender_psid,resp)
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
					ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
					manager.addItem(ctx)
					self.fbsend.sendMessage(sender_psid,resp)


					for item in r["data"]:
						text = "🏫 {}".format(item['name'].replace("Phcie","Pharmacie"))
						if item['address']:
							text = text + "\r\n{}".format(item['address'])

						if len(pharmacies):
							text = text + "\r\n\r\n{description}".format(description=item['description'])

						resp:dict = {"text":text}
						ctx = ContextMessage(message=resp,code=ContextCode.STREAMING_PHCIE)
						manager.addItem(ctx)
						self.fbsend.sendMessage(sender_psid,resp)

					manager.saveUserSearch("normal")


					


					# if random.choice([1,2]) == 2:
					# 	text = "Je t'avais deja dit 🏋️‍♂️ 🧞 ce service c'est tout simplement géniaaal 🔥🔥\r\neuhh 👀 désolé je suis un peu trop euphorique c'est temps-ci bref."
						
					# 	resp:dict = {"text":text}
					# 	ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
					# 	manager.addItem(ctx)
					# 	self.fbsend.sendMessage(sender_psid,resp)

					# 	# un git du style je suis content
					# 	resp:dict = {
					# 		"attachment": {
				 #            	"type": "image",
				 #                "payload": {
				 #                    "attachment_id": random.choice(GIPHY.HAPPY),
				 #                }
					# 		}
					# 	}
					# 	self.fbsend.sendMessage(sender_psid,resp)
					# else:
					# 	# un git du style je suis content
					# 	resp:dict = {
					# 		"attachment": {
				 #            	"type": "image",
				 #                "payload": {
				 #                    "attachment_id": random.choice(GIPHY.SUCCESS),
				 #                }
					# 		}
					# 	}
					# 	self.fbsend.sendMessage(sender_psid,resp)
					# 	time.sleep(random.choice([3,2,1]))

					if manager.check_if_user_subscribe_to_current_locality_alert() == False:

						# m = {
						# 	"nlp":{},
						# 	"quick_reply":{
						# 		"payload":"LOCALITY_ALERT_SUBSCRIPTION"
						# 	},
						# }
						# manager.handle_quick_reply(m)

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
						self.fbsend.sendMessage(sender_psid,resp)
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
					ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
					manager.addItem(ctx)
					self.fbsend.sendMessage(sender_psid,resp)

					text = "Quelle est ta localité, que je t'aide à trouver une pharmacie de garde :)"
					resp:dict = {
						"text":text
					}


					if manager.oldDataLocations is not None:
						d = manager.oldDataLocations[:10]
						resp["quick_replies"] = [{"content_type":"text","title":i,"payload":"SELECT_LOCALITY_"+i} for i in d]

						offset = len(d)
						manager.offsetDataLocations = offset
						manager.save({"offsetDataLocations":offset})

						resp["quick_replies"].append({
							"content_type":"text",
							"title":"Suivant ➡",
							"payload":"NEXT_LOCALITIES"
						})


					if manager._user.currentLocation is not None:
						if "quick_replies" not in resp:
							resp["quick_replies"] = []

						resp["quick_replies"].insert(0,{
							"content_type":"text",
							"title":"📍 {}".format(manager._user.currentLocation),
							"payload":"SELECT_MY_LOCALITY"
						})

					ctx = ContextMessage(message=resp,code=ContextCode.ASK_LOCALITY,answered=False,required=True)
					manager.addItem(ctx)
					self.fbsend.sendMessage(sender_psid,resp)
				else:
					answer = DefaultAnswer()
					answer.run(e,options)
			
		return answer


