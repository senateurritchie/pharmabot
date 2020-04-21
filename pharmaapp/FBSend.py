#!/usr/bin/python3
# -*- coding:utf-8 -*-
import requests
import os
import json

class FBSend:
	"""
	api send de facebook
	pour envoyer les differents type de message
	"""
	ENDPOINT:str = "https://graph.facebook.com/v2.6/me/messages"
	ATTACHMENT_ENDPOINT:str = "https://graph.facebook.com/v2.6/me/message_attachments"
	MESSENGER_PROFILE_ENDPOINT:str = "https://graph.facebook.com/v2.6/me/messenger_profile"
	PAGE_ACCESS_TOKEN:str = os.environ['FB_PAGE_ACCESS_TOKEN']

	def __init__(self):
		pass


	def sendAction(self,sender_psid,sender_action:str):
		"""
		permet d'envoyer les differents action lors d'une conversation
		@param sender_action pour être mark_seen|typing_on|typing_off
		"""

		payload = {"recipient":{"id":sender_psid},"sender_action":sender_action}
		params:dict = {"access_token":FBSend.PAGE_ACCESS_TOKEN}
		headers:dict = {'content-type': 'application/json'}
		
		r = requests.post(FBSend.ENDPOINT,params=params, data=json.dumps(payload), headers=headers)



	def sendMessage(self,sender_psid, message):
		"""
		permet d'envoyer les message
		"""

		#self.sendAction(sender_psid,"typing_on")
		payload = {"recipient":{"id":sender_psid},"message":message}

		params:dict = {"access_token":FBSend.PAGE_ACCESS_TOKEN}
		headers:dict = {'content-type': 'application/json'}

		r = requests.post(FBSend.ENDPOINT,params=params, data=json.dumps(payload), headers=headers)

		if r.status_code == 200:
			pass

		#self.sendAction(sender_psid,"typing_off")
		return r

	


	def saveAttachment(self,url,asset_type:str="image",is_reusable:bool = True):
		"""
		permet d'envoyer les message
		@param type image|audio|video|file
		"""
		payload = {"message":{"attachment":{"type":asset_type,"payload":{"is_reusable":is_reusable,"url":url}}}}

		params:dict = {"access_token":FBSend.PAGE_ACCESS_TOKEN}
		headers:dict = {'content-type': 'application/json'}

		r = requests.post(FBSend.ATTACHMENT_ENDPOINT,params=params, data=json.dumps(payload), headers=headers)

		if r.status_code == 200:
			pass

		return r.json()

	def setStartedMessage(self):
		"""
		permet de configurer le message d'accueil
		lorsqu'on clique sur le bouton get started
		"""
		payload = {"get_started":{"payload":"GET_STARTED"}}

		params:dict = {"access_token":FBSend.PAGE_ACCESS_TOKEN}
		headers:dict = {'content-type': 'application/json'}

		r = requests.post(FBSend.MESSENGER_PROFILE_ENDPOINT,params=params, data=json.dumps(payload), headers=headers)

		if r.status_code == 200:
			pass

		return r.json()


	def setPersitantMenu(self,sender_psid):
		"""
		permet de configurer le message d'accueil
		lorsqu'on clique sur le bouton get started
		"""
		payload = {
			"psid":sender_psid,
			"persistent_menu":[
				{
					"locale": "default",
		            "composer_input_disabled": False,
		            "call_to_actions": [
		            	{
		                	"title":"📄 Menu",
          					"type":"nested",
          					"call_to_actions":[
				                {
				                    "type": "postback",
				                    "title": "Nouvelle recherche 🔎",
				                    "payload": "MAIN_MENU",
				                },
				                {
									"type":"postback",
									"title":"Sondages 📊",
									"payload":"SURVEY_LIST"
								},
								{
									"type":"postback",
									"title":"Quizz 🏆",
									"payload":"QUIZZ_LIST"
								},
				                # {
				                #     "type": "postback",
				                #     "title": "💉 Parler à un medecin",
				                #     "payload": "CONSULTATION_REQUEST",
				                # },
          						{
				                    "type": "postback",
				                    "title": "A Propos ℹ",
				                    "payload": "ABOUT_US"
				                }
          					]
		                },
		                {
		                    "type": "postback",
		                	"title":"🇨🇮 Covid19 Stats",
							"payload":"COVID19_STATS"
		                },

		             #    {
		             #    	"title":"📢 Abonnements",
          					# "type":"nested",
          					# "call_to_actions":[
          					# 	{
				           #          "type": "postback",
				           #          "title": "📍 Localités ",
				           #          "payload": "MY_LOCALITIES_SUBSCRIPTION"
				           #      },
				           #      {
				           #          "type": "postback",
				           #          "title": "🏫 Pharmacies",
				           #          "payload": "MY_PHARMACIES_SUBSCRIPTION"
				           #      }
          					# ]
		             #    },
		                {
		                    "type": "postback",
		                    "title": "💓 Partager",
		                    "payload": "SHARE_BOT"
		                }
		             #    {
		             #    	"title":"📊 Quiz",
          					# "type":"nested",
          					# "call_to_actions":[
          					# 	{
				           #          "type": "postback",
				           #          "title": "💉 Santé",
				           #          "payload": "START_QUIZ_SANTE"
				           #      },
				           #      {
				           #          "type": "postback",
				           #          "title": "🏋️‍♀️ Bien-être",
				           #          "payload": "START_QUIZ_BIEN_ETRE"
				           #      }
          					# ]
		             #    }
		            ]
				}
			]
		}

		params:dict = {"access_token":FBSend.PAGE_ACCESS_TOKEN}
		headers:dict = {'content-type': 'application/json'}
		url = "https://graph.facebook.com/v5.0/me/custom_user_settings"

		r = requests.post(url,params=params, data=json.dumps(payload), headers=headers)

		print(r.text)

		if r.status_code == 200:
			pass

		return r.json()
