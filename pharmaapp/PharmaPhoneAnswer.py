#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .Answer import Answer
from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode


class PharmaPhoneAnswer(Answer):
	"""
	pour les reponses demandant le numéro de téléphone
	"""
	def __init__(self):
		super().__init__(["getPharmaPhone"])

	def process(self,e,options:dict=None) -> str:
		# on cherche les lieux
		communes:list = []
		quartiers:list = []
		pharmacies:list = []
		
		if "quartier" in e["entities"]:
			quartiers = [i["value"] for i in e["entities"]["quartier"] if i["confidence"] > 0.7]

		if "Commune" in e["entities"]:
			communes = [i["value"] for i in e["entities"]["Commune"] if i["confidence"] > 0.7]

		if "pharmaName" in e["entities"]:
			pharmacies = [i["value"] for i in e["entities"]["pharmaName"] if i["confidence"] > 0.7]

		answer:str = "vous avez demandé le numéro de téléphone"


		if len(pharmacies):
			if len(pharmacies) > 1 :
				answer = answer + " des pharmacies "
			else:
				answer = answer + " de la pharmacie "

			answer = answer + ", ".join(pharmacies)
		else:
			if "pharmaNombre" in e["entities"]:
				if e["entities"]["pharmaNombre"][0]["value"] == "pharmacie":
					answer = answer + " d'une pharmacie "
				else:
					answer = answer + " des pharmacies "

		if len(quartiers):
			if len(quartiers) > 1 :
				answer = answer + " des quartiers "
			else:
				answer = answer + " du quartier "

			answer = answer + ", ".join(quartiers)

			
		if len(communes):
			if len(communes) > 1 :
				answer = answer + ", dans les communes de "
			else:
				answer = answer + " dans la commune de "

			answer = answer + ", ".join(communes)

		if len(quartiers) == 0 and len(communes) == 0:
			answer = answer + " , cependant vous n'avez pas spécifié de localité prise en charge"
		

		return answer
