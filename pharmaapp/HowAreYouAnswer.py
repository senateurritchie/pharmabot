#!/usr/bin/python3
# -*- coding:utf-8 -*-

import random


from .Answer import Answer
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode


class HowAreYouAnswer(Answer):
	"""
	pour les reponses a la question quel est ton nom
	"""
	def __init__(self):
		super().__init__(["getHowAreYou"])
		self.responses = [
			"Je vais super bien.",
			"Je vais bien",
			"Tout va bien",
			"Je suis en pleine forme"
		]

	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)

		# envoi baratin 1
		m = [
			"Je ne me souviens vraiment pas la dernière fois qu'on a pris des mes nouvelles 😲",
			"tu es quelqu'un de bien 🙏",
			"Voici quelqu'un qui se souci de moi 🙏",
			"tu viens là de monter dans mon estime 🙏",
		]
		resp:dict = {
			"text":random.choice(m)
		}
		self.fbsend.sendMessage(sender_psid,resp)

		# envoi baratin 2
		resp:dict = {
			"text":"Merci de vous faire du souci pour moi ☺"
		}
		self.fbsend.sendMessage(sender_psid,resp)

		# envoi du vrai message
		text = random.choice(self.responses)
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