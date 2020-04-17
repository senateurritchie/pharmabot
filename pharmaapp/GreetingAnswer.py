#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode
import random

class GreetingAnswer(Answer):
	"""
	pour les reponses de salutation
	"""
	def __init__(self):
		super().__init__(["greeting","greetingEvening","greetingMorning"])
		self.reponses = [
			"Coucou","Hello","Salut"
		]


	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)
		manager.saveUserActivity("GREETING_ANSWER")


		text:str = ""
		code = None

		if e["entities"]["intent"][0]['value'] == "greetingMorning":
			text = "Bonjour {}".format(manager._user.first_name)
			code = ContextCode.GREETING_MORNING
			manager.saveUserActivity("GREETING_MORNING_ANSWER")


		elif e["entities"]["intent"][0]["value"] == "greetingEvening":
			text = "Bonsoir {}".format(manager._user.first_name)
			code = ContextCode.GREETING_EVENING
			manager.saveUserActivity("GREETING_EVENING_ANSWER")

		else:
			text =  random.choice(self.reponses) + " {}".format(manager._user.first_name)
			code = ContextCode.GREETING

		conv_count = manager._user.count_conversation()

		if conv_count > 1:
			m = [
				"Tres heureux de te revoir 😍",
				"Heureux de te revoir 😍",
			]
			resp:dict = {"text":random.choice(m)}
			ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
			manager.addItem(ctx)
			self.fbsend.sendMessage(sender_psid,resp)



		resp:dict = {"text":text}
		ctx = ContextMessage(message=resp,code=code)
		manager.addItem(ctx)
		self.fbsend.sendMessage(sender_psid,resp)

		if conv_count < 2:
			m = [
				"Je suis PharmaBot ton assistant personnel ⛑",
				"Je m'appelle PharmaBot ton assistant personnel ⛑",
			]
			resp:dict = {"text":random.choice(m)}
			ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
			manager.addItem(ctx)
			self.fbsend.sendMessage(sender_psid,resp)

		m = [
			"je vais t'aider à trouver une pharmacie de garde dans ta localité 🚶‍♂️🚶‍♂️🚶‍♂️",
			"tu cherches une pharmacie de garde dans ta localité 🚶‍♂️🚶‍♂️🚶‍♂️ ? et bien je vais t'aider à en trouver 😜",
			"c'est sûr que tu cherches une pharmacie de garde dans ta localité et je vais t'aider 🚶‍♂️🚶‍♂️🚶‍♂️"
		]
		resp:dict = {
			"text":random.choice(m),
		}
		ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
		manager.addItem(ctx)
		self.fbsend.sendMessage(sender_psid,resp)

		if manager.handshake == False:
			# pas encore effectuer de salutation
			manager.handshake = True
			manager.save({"handshake":manager.handshake})
			

			m = [
				"quelle est ta zone de recherche 👀",
				"pour mieux te guider dis moi ta zone de recherche 👀",
				"j'aimerais bien savoir ta zone de recherche 👀",
				"je peux savoir ta zone de recherche 🤔 ?",
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
					}
				]
			}

			if manager._user.currentZone:
				if manager._user.currentZone == 1:
					title = resp["quick_replies"][0]["title"]
					resp["quick_replies"][0]["title"] = "📍 {}".format(title)
				else:
					title = resp["quick_replies"][1]["title"]
					resp["quick_replies"][1]["title"] = "📍 {}".format(title)
					
			ctx = ContextMessage(message=resp,code=ContextCode.ASK_ZONE,answered=False,required=True)
			manager.addItem(ctx)
			self.fbsend.sendMessage(sender_psid,resp)

		else:
			# salutation deja effectuée
			# il faut verifier qu'il n'ya pas de question en suspend
			manager.process()
