#!/usr/bin/python3
# -*- coding:utf-8 -*-
import random

from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode
from .Answer import Answer

class ThankYouAnswer(Answer):
	"""
	pour les reponses de remerciement
	"""
	def __init__(self):
		super().__init__(["remerciement","congratulation"])
		self.reponses = [
			"Je t'en prie",
			"Merci c'est gentil",
			"ooh c'est vraiment gentil de ta part"
		]

	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)

		text = random.choice(self.reponses) + " {} ☺".format(manager._user.first_name)
		resp:dict = {
			"text":text
		}
		ctx = ContextMessage(message=resp,code=ContextCode.THANKS)
		manager.addItem(ctx)
		self.fbsend.sendMessage(sender_psid,resp)

		manager.process()


