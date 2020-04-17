#!/usr/bin/python3
# -*-coding:utf-8 -*-

from flask import Flask,  request,render_template as render

from wit import Wit
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from .AnswerProcessing import AnswerProcessing

from .EventDispatcher import EventDispatcher,Event
from .FBSend import FBSend

class AbstractBot(EventDispatcher):
	"""
	class abstraite pour de Bot
	"""
	name = None
	version = None
	wit:Wit = None
	answerProcessing:AnswerProcessing = None

	fbsend:FBSend = None
	messengerVerifyToken:str = None
	defered_actions = []
	webServer:Flask = None
	this = None

	def __init__(self,webServer:Flask,witAccessToken:str,answer_processor:AnswerProcessing=None):
		super().__init__()

		AbstractBot.this = self
		AbstractBot.webServer = webServer
		AbstractBot.wit = Wit(witAccessToken.split(" ")[1])
		AbstractBot.fbsend = FBSend()

		self._configuration()

		AbstractBot.messengerVerifyToken = os.environ['FB_VERIFY_TOKEN']
		AbstractBot.answerProcessing = answer_processor


	############################### DEFINITION DES METHODES PRIVEES ##############################

	def _configuration(self):
		"""
		CONFIGURATION DES ROUTES PAR DEFAUT DU BOT
		route 1: verification facebook
		route 2: reception webhooks
		"""

		webServer = AbstractBot.webServer

		AbstractBot.messenger_webhook_verify.provide_automatic_options = True
		AbstractBot.messenger_webhook_verify.methods = ['GET', 'OPTIONS',"HEAD"]
		webServer.add_url_rule("/webhook", view_func=AbstractBot.messenger_webhook_verify)

		AbstractBot.messenger_webhooks.provide_automatic_options = True
		AbstractBot.messenger_webhooks.methods = ['POST']
		webServer.add_url_rule("/webhook", view_func=AbstractBot.messenger_webhooks)

		AbstractBot.test.provide_automatic_options = True
		AbstractBot.test.methods = ['GET', 'OPTIONS',"HEAD"]
		webServer.add_url_rule("/test", view_func=AbstractBot.test)


	############################### DEFINITION DES METHODES PUBLICS ##############################

	def run(self,**kwd):
		AbstractBot.webServer.run(**kwd)


	############################### DEFINITION DES METHODES ABSTRAITES ###########################

	def handleMessage(self,sender_psid,message:dict):
		"""
		Handles messages events
		"""
		raise NotImplementedError()
		

	def handlePostback(self,sender_psid, received_postback):
		"""
		Handles messaging_postbacks events
		"""
		raise NotImplementedError()


	def handleReferral(self,sender_psid, received_referral):
		"""
		Handles messaging_referrals events
		"""
		raise NotImplementedError()

	def handleOptin(self,sender_psid, received_optin):
		"""
		Handles messaging_referrals events
		"""
		raise NotImplementedError()
	

	#################################### DEFINITION DES ROUTES ###################################
	
	def test():
		return "Test"

	def messenger_webhook_verify():

		# Parse the query params
		mode = request.args['hub.mode'];
		token = request.args['hub.verify_token'];
		challenge = request.args['hub.challenge'];

		if mode and token:
			# Checks the mode and token sent is correct
			if mode == 'subscribe' and token == AbstractBot.messengerVerifyToken:
				# Responds with the challenge token from the request
				print('WEBHOOK_VERIFIED')
				return challenge,200


		# Responds with '403 Forbidden' if verify tokens do not match
		return '',403

	def messenger_webhooks():
		import hmac
		body = request.get_json()
		app_secret = os.environ['FB_APP_SECRET']
		raw_data = request.data
		header_signature = request.headers.get("X-Hub-Signature")
		m = hmac.new(app_secret.encode(), digestmod="sha1")
		m.update(raw_data)
		expected_signature = m.hexdigest()

		if len(header_signature) != 45 or header_signature[0:5] != "sha1=":
			pass

		header_signature = header_signature[5:]
		if hmac.compare_digest(expected_signature,header_signature) == False:
			return '',400


		# Checks this is an event from a page subscription
		if body and body['object'] == 'page':
			# Iterates over each entry - there may be multiple if batched

			for entry in body["entry"]:
				# Gets the message. entry.messaging is an array, but 
				# will only ever contain one message, so we get index 0
				if "messaging" in entry:
					webhook_event = entry["messaging"][0]
					#print(webhook_event)

					# Get the sender PSID
					sender_psid = webhook_event['sender']['id']
					print('Sender PSID: ' + sender_psid)

					if 'message' in webhook_event: # evenement "message"
						received_message = webhook_event['message']

						

						thread = Thread(target=AbstractBot.this.handleMessage, args=(sender_psid, received_message))
						thread.start()

						# try:
							

						# 	with ThreadPoolExecutor(1) as executor:
						# 		f = executor.submit(AbstractBot.this.handleMessage,sender_psid, received_message)
						# 	#AbstractBot.this.handleMessage(sender_psid, received_message)
						# except Exception as e:
						# 	print(e)
						# finally:
						# 	pass
						
					elif 'postback' in webhook_event: # evenement postback
						received_postback = webhook_event['postback']
						AbstractBot.this.handlePostback(sender_psid, received_postback)

					elif 'referral' in webhook_event: 
					# evenement referral
						received_referral = webhook_event['referral']
						AbstractBot.this.handleReferral(sender_psid, received_referral)

					elif 'optin' in webhook_event: 
						# evenement optin
						received_optin = webhook_event['optin']
						AbstractBot.this.handleOptin(sender_psid, received_optin)

					elif 'delivery' in webhook_event: # evenement message envoyé
						pass

					elif 'read' in webhook_event: # evenement message lu
						pass

			# Returns a '200 OK' response to all requests
			return 'EVENT_RECEIVED',200

		# Returns a '404 Not Found' if event is not from a page subscription
		return '',404

	############################### DEFINITION DES BUILTINS EVENTS ##############################

	def on_primary_response(self,e:Event):
		"""
		cette fonction est executée soit bien avant ou bien apres que la reponse principale
		ne soit envoyée au destinataire

		tout cela depend de la position donnée
		"""
		event_type = e.data
		listToClean = []
		
		for item in AbstractBot.defered_actions:
			if item['type'] == event_type:
				listToClean.append(item)
				cbk = item['callback']
				if callable(cbk):
					cbk()

		if len(listToClean):
			for item in listToClean:
				AbstractBot.defered_actions.remove(item)


	def on_manual_instruction(self,e:Event):
		"""
		envoi le petit guide d'utilisation du service
		"""
		raise NotImplementedError()

	def on_suggest_localities(self,e:Event):
		"""
		envoi un message (template) à l'expediteur
		"""
		raise NotImplementedError()