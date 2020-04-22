#!/usr/bin/python3
# -*-coding:utf-8 -*-

import os
import pymongo
import datetime
from slugify import slugify
from .FBSend import FBSend
import logging

DATABASE_URL = os.environ["DATABASE_URL"]
client = pymongo.MongoClient(DATABASE_URL)
db = client.pharma_garde

fbsend = FBSend()

logging.basicConfig(level=logging.DEBUG)

logging.debug("Recuperation de la periode de garde en cours")

period = db.garde_period.find_one({
	"is_active":True
})
logging.debug("Recuperation de la periode de garde en cours [terminé]")

alert_offset = 0
limit = 20


if period is not None:
	logging.debug("Recuperation de la periode de garde en cours [terminé]")

	logging.debug("période en cours {}".format(period["title"].lower().capitalize()))



	if "alert_offset" in period:
		alert_offset = period["alert_offset"]

	period_id = period["_id"]

	logging.debug("Recuperation des souscripteurs aux alertes")

	#subscribers = db.user.find({}).skip(alert_offset).limit(limit).sort("_id",1)

	subscribers = db.user.find({
		"$or":[{"preferred_localities.subscribed":True},{"currentLocation":{"$exists":True}}]
		
	}).skip(alert_offset).limit(limit).sort("_id",1)

	logging.debug("Recuperation des souscripteurs aux alertes [terminé]")


	for subscriber in subscribers:

		u_name = subscriber["first_name"].lower()+" "+subscriber["last_name"].lower()

		logging.debug("Envoi à {}, ID: {}".format(u_name,str(subscriber["_id"])))


		sender_psid = subscriber["psid"]

		if subscriber["psid"] not in ["2347044518668065"]:
			continue

		alert = db.user_alert_locality.find_one({
			"period_id":period_id,
			"user_id":subscriber["_id"],
		})

		if alert is not None:
			continue

		locality_name = None
		locality = None

		if "preferred_localities" not in subscriber:
			if "currentLocation" in subscriber:
				locality_name = subscriber["currentLocation"]
		else:
			for obj in subscriber["preferred_localities"]:

				if obj["subscribed"] == False:
					continue

				locality_name = obj["name"]
				break

		if locality_name:
			locality = db.locality.find_one({
				"slug":slugify(locality_name)
			})

		resp:dict = {
			"attachment": {
            	"type": "image",
                "payload": {
                    "attachment_id":"822623314899049", 
                }
			}
		}
		fbsend.sendMessage(sender_psid,resp)

		text = "{}, une nouvelle période de tour de garde est disponible".format(subscriber["first_name"])

		resp:dict = {"text":text}
		fbsend.sendMessage(sender_psid,resp)

		
		text =  period["title"].lower().capitalize()
		resp:dict = {"text":text}
		fbsend.sendMessage(sender_psid,resp)

		alert_item = {
			"period_id":period_id,
			"user_id":subscriber["_id"],
			"locality_id":None,
			"create_at":datetime.datetime.utcnow()
		}


		if locality:
			alert_item["locality_id"] = locality["_id"]

			text =  "veux-tu consulter les pharmacies de garde de {} ?".format(locality_name.title())
			resp:dict = {
				"text":text,
				"quick_replies":[
					{
						"content_type":"text",
						"title":"✔ Oui",
						"payload":"VIEW_ALERT_{}".format(locality_name)
					},
					{
						"content_type":"text",
						"title":"🔎 Nouvelle Recherche",
						"payload":"MAIN_MENU"
					}
				]
			}
			fbsend.sendMessage(sender_psid,resp)

		else:
			resp:dict = {
				"text":"Peux-tu selectionner la zone qui t'interesse",
				"quick_replies":[
					{
						"content_type":"text",
						"title":"Abidjan",
						"payload":"ASK_ZONE_1"
					},
					{
						"content_type":"text",
						"title":"Intérieur du pays",
						"payload":"ASK_ZONE_2"
					}
				]
			}
			fbsend.sendMessage(sender_psid,resp)

		
		# db.user_alert_locality.insert_one(alert_item)

		# db.garde_period.update_one({
		# 	"_id":period_id
		# },{
		# 	"$inc":{
		# 		"alert_offset":1
		# 	}
		# })

		logging.debug("Envoi à {}, ID: {} [Terminé]".format(u_name,str(subscriber["_id"])))

else:
	logging.warn("Aucune période en cours détecté [terminé]")


logging.debug("Envois des alertes {} [terminé]".format(alert_offset))
print("\n\n")
