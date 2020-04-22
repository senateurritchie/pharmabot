#!/usr/bin/python3
# -*-coding:utf-8 -*-

from flask import Flask,  request, make_response as response, abort, redirect,url_for,render_template as render

from wit import Wit
import json
import os
import requests
from io import BytesIO,StringIO
import  subprocess
import  re
import time
import datetime

from dotenv import load_dotenv
load_dotenv()

from .AbstractBot import AbstractBot

from .AnswerProcessing import AnswerProcessing
from .PharmaAnswerProcessing import PharmaAnswerProcessing
from .GetStartedAnswer import GetStartedAnswer
from .GreetingAnswer import GreetingAnswer
from .HowAreYouAnswer import HowAreYouAnswer
from .PharmaGardeAnswer import PharmaGardeAnswer
from .PharmaPhoneAnswer import PharmaPhoneAnswer
from .ThankYouAnswer import ThankYouAnswer
from .WhatIsYourNameAnswer import WhatIsYourNameAnswer
from .ConfirmationAnswer import ConfirmationAnswer
from .ServiceLocalityAnswer import ServiceLocalityAnswer
from .GoodbyeAnswer import GoodbyeAnswer
from .MainMenuAnswer import MainMenuAnswer
from .NewSearchAnswer import NewSearchAnswer
from .HaveConsultationAnswer import HaveConsultationAnswer
from .IsTestAnswer import IsTestAnswer

from .ContextMessageManager import ContextMessage,ContextMessageManager,ContextCode,ContextMessageAuthor
from .EventDispatcher import EventDispatcher,Event

from .modules.security import bp as securBP,_is_granted
from .modules.admin import bp as adminBP



app = Flask(__name__)

app.secret_key = b"v\xa1\x16\xfd\xcb\xa4\x97'\x94\xb7\x04\xa5\xb4H\xcc\x16m\xc6\xc0\xef\x97^\xdeF"
app.config['MAX_CONTENT_LENGTH'] = 700 * 1024 * 1024
app.register_blueprint(securBP)
app.register_blueprint(adminBP)


@app.context_processor
def passer_aux_templates_jinja2():
    return dict(is_granted=_is_granted)

class PharmaBot(AbstractBot):
	"""
	application gerant les webhooks de facebook
	"""
	name = "PharmaBot"
	version = "1.0.0"

	def __init__(self,witAccessToken):
		answer_processor = PharmaAnswerProcessing()
		super().__init__(app,witAccessToken, answer_processor=answer_processor)

		serviceLocalityAnswer = ServiceLocalityAnswer()
		getStartedAnswer = GetStartedAnswer()
		greetingAnswer = GreetingAnswer()
		goodbyeAnswer = GoodbyeAnswer()
		howAreYouAnswer = HowAreYouAnswer()
		thankYouAnswer = ThankYouAnswer()
		whatIsYourNameAnswer = WhatIsYourNameAnswer()
		confirmationAnswer = ConfirmationAnswer()
		pharmaGardeAnswer = PharmaGardeAnswer()
		pharmaPhoneAnswer = PharmaPhoneAnswer()
		mainMenuAnswer = MainMenuAnswer()
		newSearchAnswer = NewSearchAnswer()
		haveConsultationAnswer = HaveConsultationAnswer()
		isTestAnswer = IsTestAnswer()



		answer_processor.append(getStartedAnswer)
		answer_processor.append(greetingAnswer)
		answer_processor.append(goodbyeAnswer)
		answer_processor.append(howAreYouAnswer)
		answer_processor.append(thankYouAnswer)
		answer_processor.append(whatIsYourNameAnswer)
		answer_processor.append(confirmationAnswer)
		answer_processor.append(serviceLocalityAnswer)
		answer_processor.append(pharmaGardeAnswer)
		answer_processor.append(pharmaPhoneAnswer)
		answer_processor.append(mainMenuAnswer)
		answer_processor.append(newSearchAnswer)
		answer_processor.append(haveConsultationAnswer)
		answer_processor.append(isTestAnswer)


	#################################### DEFINITION DES ROUTES ###################################

	@app.route("/")
	def index():
		return render("index.html.jinja2")

	@app.route("/coming-soon")
	def coming_soon():
		return render("coming-soon.html.jinja2")

	@app.route("/privacy-policy")
	@app.route("/politique-de-confidentialite")
	def privacy_policy():
		return render("privacy-policy.html.jinja2")

	@app.route("/robots.txt")
	def robots():
		data = ""
		with open("static/robots.txt","r") as f:
			data = f.read()
		return data,200

	@app.route("/webview")
	def webview():
		resp = response(render("webview.html.jinja2"))
		resp.headers.set("X-Frame-Options","ALLOW-FROM https://www.facebook.com/")
		resp.headers.set("X-Frame-Options","ALLOW-FROM https://www.messenger.com/")
		return resp

	@app.route("/speech")
	def apiSpeech():
		audio_path = "https://cdn.fbsbx.com/v/t59.3654-21/61837937_477838826294690_28197843277709312_n.mp4/audioclip-1560853217000-2809.mp4?_nc_cat=110&_nc_ht=cdn.fbsbx.com&oh=6c1e7dfb8c70243e58af5dd9366616be&oe=5D0B433F"

		r = re.search(r"(audioclip.+)\.mp4",audio_path)
		filename = r.group(1)
		filename = "static/{}.flac".format(filename)
		cmd = 'ffmpeg -i "{}"  -c:a flac "{}"'.format(audio_path,filename)

		subprocess.run(cmd)

		resp = None

		with open(filename, "rb") as f:
			#f = BytesIO(r.content)
			resp = PharmaBot.wit.speech(f, None, {'Content-Type':"audio/flac"})
			#f.close()

		if resp is not None:
			return json.dumps(resp),200

		return '{}',200
		

	@app.route("/message", methods=["POST"])
	def apiMessage():
		q = request.form['q']
		resp = PharmaBot.wit.message(q)
		answer = PharmaBot.answerProcessing.process(resp)
		resp["response"] = answer
		resp = response(json.dumps(resp),200)
		resp.mimetype = "application/json"
		return resp

	@app.errorhandler(404)
	def view404(error):
		return render("404.html.jinja2"),404

	@app.errorhandler(403)
	def view403(error):
		return render("403.html.jinja2"),403

	@app.errorhandler(500)
	def view500(error):
		return "ma jolie page 500", 500



	############################### DEFINITION DES METHODES ABSTRAITES ###########################

	def handleMessage(self,sender_psid,message):
		"""
		Handles messages events
		"""
		resp = {}
		PharmaBot.fbsend.sendAction(sender_psid,"mark_seen")

		# on verifie si le message contient une proprieté text
		manager = ContextMessageManager(user_id=sender_psid)
		manager.save({"last_presence":datetime.datetime.utcnow()})

		if manager._user.has_new_menu:
			"""
			il faut envoyer le nouveau menu
			"""
			PharmaBot.fbsend.setPersitantMenu(manager._user.psid)
			manager.save({"has_new_menu":False})



		if "text" in message:
			
			te = manager.handle_quick_reply(message)

			if te is None:

				if manager._user.in_consulting:
					# il faut retrouver la consultation
					manager.processConsultingFlow(message)
				else:
					PharmaBot.answerProcessing.process(message["nlp"],{"sender_psid":sender_psid,"text":message["text"]})

		elif "attachments" in message:
			audio_attachment = message['attachments'][0]


			if manager._user.in_consulting:
				# il faut retrouver la consultation
				manager.processConsultingFlow(message)

			elif manager._user.question_processing:
				message["nlp"] = {}
				te = manager.handle_quick_reply(message)
			else:
				if audio_attachment['type'] == "audio":
					audio_path = audio_attachment['payload']["url"]
					r = re.search(r"(audioclip.+)\.mp4",audio_path)
					filename = r.group(1)
					filename = "static/{}.flac".format(filename)
					cmd = 'ffmpeg -y -i "{}"  -c:a flac "{}"'.format(audio_path,filename)

					# envoyer une action = "en train d'écrire"
					PharmaBot.fbsend.sendAction(sender_psid,"typing_on")
					
					p = subprocess.run(cmd, shell=True)

					if p.returncode == 0:

						with open(filename, "rb") as f:
							message = PharmaBot.wit.speech(f, None, {'Content-Type':"audio/flac"})

							if manager.handle_quick_reply(message) is None:
								PharmaBot.answerProcessing.process(message,{"sender_psid":sender_psid})



	def handlePostback(self,sender_psid, received_postback):
		"""
		Handles messaging_postbacks events
		"""
		manager = ContextMessageManager(user_id=sender_psid)
		PharmaBot.fbsend.sendAction(sender_psid,"mark_seen")

		if manager._user.has_new_menu:
			"""
			il faut envoyer le nouveau menu
			"""
			PharmaBot.fbsend.setPersitantMenu(manager._user.psid)
			manager.save({"has_new_menu":False})

		# from threading import Thread


		# def test():
		# 	print(PharmaBot.fbsend.saveAttachment("http://160.120.150.85:5000/static/demo.mp4","video"))
		
		# thread = Thread(target=test)
		# thread.start()

		m = {
			"nlp":{},
			"quick_reply":{
				"payload":received_postback["payload"]
			},
		}
		manager.handle_quick_reply(m)

	def handleReferral(self,sender_psid, received_referral):
		"""
		Handles messaging_referrals events
		"""
		manager = ContextMessageManager(user_id=sender_psid)

		if manager._user.has_new_menu:
			"""
			il faut envoyer le nouveau menu
			"""
			PharmaBot.fbsend.setPersitantMenu(manager._user.psid)
			manager.save({"has_new_menu":False})



		referrals = [
			"CONSULTATION_REQUEST"
		]

		if received_referral["ref"] not in referrals:
			return

		m = {
			"nlp":{},
			"quick_reply":{
				"payload":received_referral["ref"]
			},
		}
		manager.handle_quick_reply(m)


		

	def handleOptin(self,sender_psid, received_optin):
		"""
		Handles messaging_referrals events
		"""
		manager = ContextMessageManager(user_id=sender_psid)

		if manager._user.has_new_menu:
			"""
			il faut envoyer le nouveau menu
			"""
			PharmaBot.fbsend.setPersitantMenu(manager._user.psid)
			manager.save({"has_new_menu":False})

		m = {
			"nlp":{},
			"quick_reply":received_optin,
		}
		manager.handle_quick_reply(m)



		
	########################### DEFINITION DES BUILTINS EVENTS ##########################
	