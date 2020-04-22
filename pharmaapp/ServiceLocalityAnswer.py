#!/usr/bin/python3
# -*- coding:utf-8 -*-
from bs4 import BeautifulSoup
import requests
import re
import random
import time

from .OfficineUpdater import OfficineUpdater
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode,GIPHY
from .Answer import Answer

class ServiceLocalityAnswer(Answer):
	"""
	pour les reponses demandant les localités dispolible pour le service
	"""
	def __init__(self):
		super().__init__(["getServiceLocations"])
		self.scrappingUrl = "https://www.abidjan.net/inc/abidjan/inc_pharmacie.js"


	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)


		intent = e["entities"]["intent"][0]
		zoneId = None
		if "zoneName" in e["entities"]:
			zoneId = 1 if e["entities"]["zoneName"][0]["value"] == "abidjan" else 2


		m = [
			"Un instant que je fouine un peu",
			"Laissez moi chercher un peu.",
			"Je te reviens sous peu"
		]
		resp:dict = {
			"text":random.choice(m)
		}
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
		eeee = self.fbsend.sendMessage(sender_psid,resp)
		
		ofm = OfficineUpdater()
		opts = {}

		if zoneId is not None:
			opts["zone"] = zoneId
		else:
			if manager._user.currentZone:
				opts["zone"] = manager._user.currentZone
			else:
				opts["zone"] = 1


		data = ofm.loadLocalities(opts)

		if len(data):
			data = sorted(data)

			if "zone" in opts:
				manager.oldDataLocations = data
				manager.save({"oldDataLocations":data})

			text = 'voilà...😎'
			resp:dict = {
				"text":text
			}
			self.fbsend.sendMessage(sender_psid,resp)

			last = ""
			text = "\r\n".join(["▪ {}".format(i) for i in data])

			resp:dict = {
				"text":text
			}
			self.fbsend.sendMessage(sender_psid,resp)

			m = [
				"Quelle est ta localité pour que j'affiche les pharmacies de garde 🔥",
				"Quelle localité choisis-tu pour que j'affiche les pharmacies de garde 🔥",
				"Peux-tu saisir ta localité pour que j'affiche les pharmacies de garde 🔥",
				"Peux-tu saisir ta localité, pour que j'affiche les pharmacies de garde 🔥",
			]
			d = data[:10]
			resp:dict = {
				"text":random.choice(m),
				"quick_replies":[{"content_type":"text","title":i,"payload":"SELECT_LOCALITY_"+i} for i in d]
			}

			offset = len(d)
			manager.offsetDataLocations = offset
			manager.save({
				"offsetDataLocations":offset,
				"question_processing":"NEW_SEARCH"
			})


			resp["quick_replies"].append({
				"content_type":"text",
				"title":"Suivant ➡",
				"payload":"NEXT_LOCALITIES"
			})


			if manager._user.currentLocation:
				resp["quick_replies"].insert(0,{
					"content_type":"text",
					"title":"📍 {}".format(manager._user.currentLocation),
					"payload":"SELECT_MY_LOCALITY"
				}) 

			self.fbsend.sendMessage(sender_psid,resp)

		else:
			text = "Ooops...il semble que j'ai un petit souci"
			resp:dict = {
				"text":text
			}
			ctx = ContextMessage(message=resp,code=ContextCode.LOCALITY_ALERT)
			manager.addItem(ctx)
			self.fbsend.sendMessage(sender_psid,resp)

			# text = "je dois informer urgemment des responsables"
			# resp:dict = {
			# 	"text":text
			# }
			# ctx = ContextMessage(message=resp,code=ContextCode.LOCALITY_ALERT)
			# manager.addItem(ctx)
			# self.fbsend.sendMessage(sender_psid,resp)
			manager.process()





