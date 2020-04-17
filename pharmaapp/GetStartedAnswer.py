#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode
import random

class GetStartedAnswer(Answer):
	"""
	pour les reponses de salutation
	"""
	def __init__(self):
		super().__init__(["getstarted"])
		self.reponses = [
			"Coucou","Hello","Salut"
		]


	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)

		m = {
			"nlp":{},
			"quick_reply":{
				"payload":"GET_STARTED"
			},
		}
		manager.handle_quick_reply(m)