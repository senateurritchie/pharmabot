#!/usr/bin/python3
# -*- coding:utf-8 -*-
import random
from .EventDispatcher import EventDispatcher
from .FBSend import FBSend

class Answer(EventDispatcher):
	"""
	rendu des type de reponse
	"""
	def __init__(self,name:list):
		super().__init__()

		self.fbsend = FBSend()
		self._name:list = name
		self.responses = []
		self.witResponse = None

	def run(self,witResponse,options:dict=None) -> str:
		return self.process(witResponse,options)

	def process(self,witResponse,options:dict=None):
		raise NotImplementedError("la methode process doit être implementée dans les classes filles")