#!/usr/bin/python3
# -*- coding:utf-8 -*-

from .Answer import Answer
from .ContextMessageManager import ContextMessageManager

class HaveConsultationAnswer(Answer):
	"""
	pour les reponses de salutation
	"""
	def __init__(self):
		super().__init__(["haveConsultation"])
		

	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)

		m = {
			"nlp":{},
			"quick_reply":{
				"payload":"CONSULTATION_REQUEST"
			},
		}
		manager.handle_quick_reply(m)

		