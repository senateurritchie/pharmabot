#!/usr/bin/python3
# -*- coding:utf-8 -*-
import random
from .Answer import Answer

class AnswerProcessing:
	"""
	module du bot servant a repondre aux messages recus
	"""
	def __init__(self,data:list = []):

		for i in data:
			if not isinstance(i,Answer):
				raise RuntimeError

		self.data:list = data


	def append(self,answer:Answer):
		"""
		permet d'ajouter un module de reponse
		"""

		if not isinstance(answer,Answer):
			raise RuntimeError

		self.data.append(answer)
		return self

	def remove(self,answer:Answer):
		"""
		permet de supprimer un module de reponse
		"""
		self.data.remove(answer)
		return self

	def process(self,e,options:dict=None):
		"""
		methode abstraite de traitement des messages recu
		"""
		raise NotImplementedError()