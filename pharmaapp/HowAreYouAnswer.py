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
		manager.saveUserActivity("HOW_ARE_YOU_ANSWER")

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
		ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
		manager.addItem(ctx)
		self.fbsend.sendMessage(sender_psid,resp)

		# envoi baratin 2
		resp:dict = {
			"text":"Merci de vous faire du souci pour moi ☺"
		}
		ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
		manager.addItem(ctx)
		self.fbsend.sendMessage(sender_psid,resp)

		# envoi du vrai message
		text = random.choice(self.responses)
		resp:dict = {"text":text}
		ctx = ContextMessage(message=resp,code=ContextCode.IM_FINE)
		manager.addItem(ctx)
		self.fbsend.sendMessage(sender_psid,resp)

		if manager.currentLocation is None:
			# si on na pas encore demander la localisation du visiteur
			m = [
				"Pour m'avoir temoigner ton attention, je vais t'aider à trouver ce que tu cherches",
				"Comme une personne reconnaissante je vais bien t'aider",
				"Tiens, tiens voici ce que je te propose pour commencer",
			]
			resp:dict = {
				"text":random.choice(m),
			}
			ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
			manager.addItem(ctx)
			self.fbsend.sendMessage(sender_psid,resp)


		manager.process()