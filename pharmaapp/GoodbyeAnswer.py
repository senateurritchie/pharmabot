#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode
import random

class GoodbyeAnswer(Answer):
	"""
	pour les reponses de salutation
	"""
	def __init__(self):
		super().__init__(["goodbye"])
		self.reponses = [
			"à bientôt",
			"portes toi bien",
			"aurevoir",
			"a plus, portes toi bien",
			"bye",
			"à tres bientôt"
		]

	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)

		if manager.goodbye == False:
			# si on a pas encore dis aurevoir au visiteur
			manager.goodbye = True
			messages = [
				"🙋‍♀️ J'ai vraiment été tres honnoré de votre passage ☺",
				"🙋‍♀️ J'ai vraiment été tres ravi de votre passage ☺",
				"🙋‍♀️ J'ai vraiment ce petit moment ☺",
				"🙋‍♀️ Ravi de t'avoir connu ☺",
				"🙋‍♀️ J'espère bien qu'on se retrouvera pour d'autres moment ☺",
			]
			resp:dict = {"text":random.choice(messages)}
			self.fbsend.sendMessage(sender_psid,resp)

		# envoi message 2
		text = random.choice(self.reponses)
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