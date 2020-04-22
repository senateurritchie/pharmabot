#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode

class IsTestAnswer(Answer):
	"""
	pour les reponses de salutation
	"""
	def __init__(self):
		super().__init__(["isTest"])


	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)

		text:str = "Je sais que tu as hyper envie de me tester 😍 💪"
		resp:dict = {"text":text}
		self.fbsend.sendMessage(sender_psid,resp)

		text:str = "Mais mes connaissances ne sont pas générales 😞. je te serai certainement utile dans la recherche de pharmacies de gardes ou la mise en relation avec un medecin 😜"
		resp:dict = {
			"text":text,
		}
		self.fbsend.sendMessage(sender_psid,resp)

		m = {
			"nlp":{},
			"quick_reply":{
				"payload":"MAIN_MENU"
			},
			"insta":2
		}
		manager.handle_quick_reply(m)

		