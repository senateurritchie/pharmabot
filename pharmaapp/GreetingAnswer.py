#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode
import random
import datetime

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


		text:str = ""

		if e["entities"]["intent"][0]['value'] == "greetingMorning":
			text = "Bonjour {}".format(manager._user.first_name)


		elif e["entities"]["intent"][0]["value"] == "greetingEvening":
			text = "Bonsoir {}".format(manager._user.first_name)

		else:
			text =  random.choice(self.reponses) + " {}".format(manager._user.first_name)

		now = datetime.datetime.utcnow()
		last_presence = manager._user.last_presence

		elapsed_time = now - last_presence

		if elapsed_time.seconds//3600 > 24:
			"""
			apres au moins 24 de retour d'un utilisateur
			"""
			m = [
				"Tres heureux de te revoir 😍",
				"Heureux de te revoir 😍",
			]
			resp:dict = {"text":random.choice(m)}
			self.fbsend.sendMessage(sender_psid,resp)

		resp:dict = {"text":text}
		self.fbsend.sendMessage(sender_psid,resp)

		m = {
			"nlp":{},
			"quick_reply":{
				"payload":"MAIN_MENU"
			},
			"insta":2
		}
		manager.handle_quick_reply(m)
		
