#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
import random
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode

class MainMenuAnswer(Answer):
	"""
	pour les reponses de retour au menu principal
	"""
	def __init__(self):
		super().__init__(["getMainMenu"])

	def process(self,e,options:dict=None) -> str:
		sender_psid = options["sender_psid"]
		manager = ContextMessageManager(user_id=sender_psid)
		m = {
			"nlp":{},
			"quick_reply":{
				"payload":"MAIN_MENU"
			}
		}
		manager.handle_quick_reply(m)