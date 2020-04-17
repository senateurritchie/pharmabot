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
		manager.saveUserActivity("ISTEST_ANSWER")

		text:str = "Je sais que tu as hyper envie de me tester 😍 💪"
		resp:dict = {"text":text}
		ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
		manager.addItem(ctx)
		self.fbsend.sendMessage(sender_psid,resp)

		text:str = "Mais mes connaissances ne sont pas générales 😞. je te serai certainement utile dans la recherche de pharmacies de gardes ou la mise en relation avec un medecin 😜"
		resp:dict = {
			"text":text,
			"quick_replies":[
				{
					"content_type":"text",
					"title":"🔎 Tour de garde",
					"payload":"MAIN_MENU"
				},
				{
					"content_type":"text",
	                "title": "👨‍⚕️ Parler à un medecin",
	                "payload": "CONSULTATION_REQUEST",
				}
			]
		}
		ctx = ContextMessage(message=resp,code=ContextCode.VERBOSE)
		manager.addItem(ctx)
		self.fbsend.sendMessage(sender_psid,resp)

		