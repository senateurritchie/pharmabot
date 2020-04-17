#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
import random
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode

class NewSearchAnswer(Answer):
	"""
	pour les demande de nouvelles recherches
	"""
	def __init__(self):
		super().__init__(["getNewSearch"])

	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)
		m = {
			"nlp":{},
			"quick_reply":{
				"payload":"NEW_SEARCH"
			}
		}
		manager.handle_quick_reply(m)