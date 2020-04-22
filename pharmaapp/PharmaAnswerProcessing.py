#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .DefaultAnswer import DefaultAnswer
from .PharmaGardeAnswer import PharmaGardeAnswer
from .AnswerProcessing import AnswerProcessing
from .ContextMessageManager import ContextMessageManager

class PharmaAnswerProcessing(AnswerProcessing):
	"""
	module du bot servant a repondre aux messages recus
	"""

	def __init__(self,data:list = []):
		super().__init__(data)

	def process(self,e,options:dict=None):


		if "location" in e["entities"]:
			e["entities"]['Commune'] = e["entities"]['location']
			if "suggested" in e["entities"]['Commune'][0]:
				del e["entities"]['Commune'][0]["suggested"]

			del e["entities"]['location']


		if "intent" in e["entities"]:
			if len(e["entities"]["intent"]):
				intent = e["entities"]["intent"][0]

				for answer in self.data:
					if intent["value"] in answer._name:
						return answer.run(e,options)

		elif "Commune" in e["entities"]:

			if "suggested" not in e["entities"]["Commune"][0]:
				answer = PharmaGardeAnswer()
				return answer.run(e,options)
			

		elif "quartier" in e["entities"]:

			if "suggested" not in e["entities"]["quartier"][0]:
				answer = PharmaGardeAnswer()
				return answer.run(e,options)
			
		answer = DefaultAnswer()
		return answer.run(e,options)