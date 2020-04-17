#!/usr/bin/python3
# -*- coding:utf-8 -*-
import random

from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode
from .Answer import Answer

class WhatIsYourNameAnswer(Answer):
	"""
	pour les reponses a la question quel est ton nom
	"""
	def __init__(self):
		super().__init__(["getName"])

		name = "Pharma Bot"
		self.responses = [
			"Je m'appelle {}.".format(name),
			"Vous pouvez m'appeller {}.".format(name),
			"Mon nom est {}.".format(name),
			"{} est mon nom.".format(name)
		]

	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)

		if manager.is_ask_name == False:
			# si on a pas encore repondu a cette question
			manager.is_ask_name = True
			manager.save({"is_ask_name":manager.is_ask_name})
			text = "😲 là... je pense que nous commençons à tisser...de veritables liens toi et moi 🙏"
			resp:dict = {
				"text":text
			}
			ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
			manager.addItem(ctx)
			self.fbsend.sendMessage(sender_psid,resp)

			text = "c'est tres gentil de vouloir savoir comment je m'appelle 🙏"
			resp:dict = {
				"text":text
			}
			ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
			manager.addItem(ctx)
			self.fbsend.sendMessage(sender_psid,resp)

		
		text = random.choice(self.responses)
		resp:dict = {
			"text":text
		}
		ctx = ContextMessage(message=resp,code=ContextCode.ANSWER_WITH_MY_NAME)
		manager.addItem(ctx)
		self.fbsend.sendMessage(sender_psid,resp)

		manager.process()
