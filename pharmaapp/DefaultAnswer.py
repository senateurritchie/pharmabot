#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode

import random

class DefaultAnswer(Answer):
	"""
	pour les reponses par default
	lorsqu'on ne trouve aucun événement correspondant
	"""
	def __init__(self):
		super().__init__(["default"])
		self.responses = [
			"Désolé, je n'ai pas vraiment compris ce que tu as voulu me dire mais j'apprends vite et bien 💪",
			"Il m'arrive de perdre le fil et de ne pas tout comprendre mais j'y travaille tous les jours 😊",
			"je ne peux pas te repondre, parce que je ne t'ai pas bien saisi mais je me remets à l'entrainement dés maintenant ! 💪",
			"Je m'avoue vaincu pour cette fois, je n'ai pas compris... 😭 Je me remets à l'entrainement dés maintenant ! 💪",
			"Tout va trop vite pour mon petit cerveau... 🤔 Je travaille à l'améliorer, promis ! ✊"
		]

	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)

		text = random.choice(self.responses)
		resp:dict = {"text":text}
		self.fbsend.sendMessage(sender_psid,resp)

		manager.save({
			"question_processing":None,
		})

		manager.process()