#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
import random
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode

class ConfirmationAnswer(Answer):
	"""
	pour les reponses a la question quel est ton nom
	"""
	def __init__(self):
		super().__init__(["answerConfirm"])

		self.responses = [
			"bien sûr :)",
			"serieux :)",
			"bien sûr que oui :)",
			"oui :)",
			"c'est vrai :)",
			"tout à fait :)",
		]

	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)
		manager.saveUserActivity("CONFIRMATION_ANSWER")

		text = random.choice(self.responses)
		resp:dict = {"text":text}
		self.fbsend.sendMessage(sender_psid,resp)

		manager.save({
			"question_processing":None,
		})

		manager.process()