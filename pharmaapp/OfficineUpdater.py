#!/usr/bin/python3
# -*- coding:utf-8 -*-

from bs4 import BeautifulSoup
from bs4.element import NavigableString

import requests
import re
import datetime
import time
import os
import csv
import json
from threading import Thread
import logging
from slugify import slugify
import pymongo
import sys
import argparse


from .EventDispatcher import EventDispatcher,Event

DATABASE_URL = os.environ["DATABASE_URL"]
client = pymongo.MongoClient(DATABASE_URL)
db = client.pharma_garde

logging.basicConfig(level=logging.DEBUG)


class OfficineUpdater(EventDispatcher):
	"""docstring for OfficineUpdater"""
	def __init__(self):
		super().__init__()

		self.url = "https://www.dpml.ci/fr/liste-officines"
		self.gardeUrl = "https://www.abidjan.net/inc/abidjan/inc_pharmacie.js"
		self.pageUrlEndpoint = "https://www.abidjan.net/sante/pharmacies/"
		self.user_agent = "Pharma Bot/1.0.0"

	def addOfficialPharmacy(self,payload,db=None):

		payload["name"] = payload["name"].replace("saint ","st ").lower()
		payload["name"] = payload["name"].replace("sainte ","ste ").lower()
		payload["slug"] = payload["slug"].replace("saint-","st-")
		payload["slug"] = payload["slug"].replace("sainte-","ste-")

		if "locality_id" not in payload:
			locality = self.addLocality({
				"name":payload["locality"].strip(),
				"slug":payload["locality_slug"],
				"zone":payload["zone"]
			},db)

			payload["locality_id"] = locality["_id"]


		pharmacy = db.garde_pharmacy.find_one({
			"locality_id":payload["locality_id"],
			"slug":payload["slug"]
		})

		if pharmacy is None:
			_id = db.garde_pharmacy.insert_one(payload).inserted_id
			pharmacy = db.garde_pharmacy.find_one({
				"_id":_id,
			})


		return pharmacy

	def addLocality(self,payload,db=None):
		locality = db.locality.find_one({
			"slug":payload["slug"]
		})

		if locality is None:
			_id = db.locality.insert_one(payload).inserted_id
			locality = db.locality.find_one({
				"_id":_id
			})

		return locality

	def createOfficialPharmacyDB(self):


		periods = db.garde_period.find({}).sort("_id",-1)

		db.garde_pharmacy.delete_many({})

		for i,period in enumerate(periods):
			gardes = db.garde.find({"garde_period_id":period["_id"]})

			for garde in gardes:

				locality = self.addLocality({
					"name":garde["locality"].strip(),
					"slug":garde["locality_slug"],
					"zone":garde["zone"]
				},db)
				if "zone" not in locality:
					db.locality.update_one({
						"_id":locality["_id"]
					},{
						"$set":{
							"zone":garde["zone"]
						}
					})
				garde["locality_id"] = locality["_id"]


				garde["slug"] = garde["pharmacy_slug"]
				garde["name"] = garde["pharmacy"]
				garde["create_at"] = datetime.datetime.utcnow()

				del garde["_id"]
				del garde["pharmacy_slug"]
				del garde["pharmacy"]
				del garde["locality_slug"]
				del garde["locality"]
				del garde["zone"]

				pharmacy = self.addOfficialPharmacy(garde,db)

	def checkNewGardePeriod(self) -> bool:
		"""
		permet de verifier si une nouvelle periode de garde est disponible
		"""


		date = datetime.date.today()

		current_date = datetime.datetime(date.year,date.month,date.day)
		isExists = db.garde_period.find_one({
			"is_active":True,
			"start":{"$lte":current_date},
			"end":{"$gte":current_date},
		})

		return True if isExists is None else False

	def loadLocalities(self,opts:dict={}) -> list:
		"""
		Recupere tout les localités disponible ce jour pour le service
		"""


		date = datetime.date.today()

		current_date = datetime.datetime(date.year,date.month,date.day)
		# isExists = db.garde_period.find_one({
		# 	"is_active":True,
		# 	"start":{"$lte":current_date},
		# 	"end":{"$gte":current_date},
		# })

		# if isExists is None:
		# 	self.saveGardeList()

		stages = [
			{
				"$lookup":{
					"from":"garde_period",
					"localField":"garde_period_id",
					"foreignField":"_id",
					"as":"period"
				}
			},
			{"$match":{"period.is_active":True}},
			{"$group":{"_id":"$locality"}},
			{"$sort":{"_id":1}}
		]

		if "zone" in opts:
			zone = int(opts["zone"])
			stages[1]["$match"]["zone"] = zone

		results = db.garde.aggregate(stages)
		results = [i["_id"] for i in results ]

		return results



	def search(self,quartier=[],commune=[],pharmacie=[]):
		"""
		Recherche les pharmacies de garde disponible

		@param name represente le nom de la pharmacie a rechercher
		@param locality le nom de la commune à rechercher
		"""


		date = datetime.date.today()

		current_date = datetime.datetime(date.year,date.month,date.day)
		period = db.garde_period.find_one({
			"is_active":True,
			#"start":{"$lte":current_date},
			#"end":{"$gte":current_date},
		})

		if period is None:
			return
			#self.saveGardeList()

		stages = [
			{
				"$lookup":{
					"from":"garde_period",
					"localField":"garde_period_id",
					"foreignField":"_id",
					"as":"period"
				}
			},
			{"$match":{"period.is_active":True}},
			{"$sort":{"_id":1}}
		]

		if len(pharmacie):
			pharmacie_ = slugify(pharmacie[0])
			stages[1]["$match"]["pharmacy_slug"] = {"$regex":"^{}".format(pharmacie_)}
		elif len(commune):
			commune_ = slugify(commune[0])
			stages[1]["$match"]["locality_slug"] = commune_

		elif len(quartier):
			quartier_ = slugify(quartier[0])
			stages[1]["$match"]["locality_slug"] = quartier_

		# if "zone" in opts:
		# 	zone = int(opts["zone"])
		# 	stages[1]["$match"]["zone"] = zone

		r = db.garde.aggregate(stages)
		results:dict = {"period":period["title"],"place":None,"data":[]}

		for row in r:

			if len(pharmacie) and not row["address"]:
				row["address"] = "situation indisponible"
				if "page_url" in row:
					page_url = row["page_url"]

					rr = requests.get(page_url,headers={"User-Agent":self.user_agent})
					if rr.status_code == 200:
					 	html2 = BeautifulSoup(rr.text,"lxml")
					 	container = html2.find("div",id="module")
					 	box2 = container.find("div",class_="boxBottomS2")

					 	for rrr in box2.find("h4").contents:
					 		if not isinstance(rrr, NavigableString):
					 			continue

					 		situation = rrr.string.strip()

					 		if situation.startswith("Direction") and len(situation) > 12:
					 			row["address"] = situation[11:].strip(" -/.").capitalize()

					 			row["address"] = re.sub(r"/",r" ",row["address"])
					 			row["address"] = re.sub(r"`",r"'",row["address"])
					 			row["address"] = re.sub(r"iii|III",r"3",row["address"])
					 			row["address"] = re.sub(r"ii|II",r"2",row["address"])

					 			break

					 	# mise a jour de la situation geographique dans la base de données
					 	if row["address"] is not None:
					 		db.garde.update_one({
					 			"_id":row["_id"]
					 		},{
					 			"$set":{
					 				"address":row["address"]
					 			}
					 		})

					 		locality = db.locality.find_one({
					 			"slug":row["locality_slug"]
					 		})

					 		db.garde_pharmacy.update_one({
					 			"locality_id":locality["_id"],
					 			"slug":row["pharmacy_slug"]
					 		},{
					 			"$set":{
					 				"address":row["address"]
					 			}
					 		})

			pharma_name = row["pharmacy"].lower().title()
			pharma_owner = row["owner"]
			pharma_description = row["address"]

			if "page_url" in row:
				pharma_page = row["page_url"]

				pharma_address = "-".join(row["contacts"])
				pharma_address = re.sub(r"[ \.-](\d{2})",r" \1",pharma_address)
				pharma_address = re.sub(r"/",r"-",pharma_address)
				pharma_address = pharma_address.split("-")
			else:
				pharma_address = []
				for contact in row["contacts"]:
					contact = re.sub(r"(TEL\.?)",r"",contact)
					contact = "TEL. {}".format(contact.strip())
					pharma_address.append(contact)


			pharma_address = "\r\n".join(ii.strip(" -/") for ii in pharma_address)

			
			item = {
				"name":pharma_name,
				"owner":pharma_owner,
				"address":pharma_address,
				#"page":pharma_page,
				"description":pharma_description,
			}

			if "page_url" in row:
				item["page"] = pharma_page

			results["data"].append(item)
			results["place"] = row["locality"]

		return results



	def get_zone(self,loc):
		ZONE_A = [
			"2 plateaux","abobo","abobo pk 18","abobodoume","adjame","adjouffou",
			"anyama","attecoube","bingerville","cocody","locodjoro","marcory",
			"plateau","port bouet","riviera","treichville","vridi","williamsville",
			"yopougon","koumassi","gonzaq","anoumabo"
		]

		if loc.lower() in ZONE_A:
			return 1
		else:
			return 2

	def get_month_number(self,name):
		months = [
			"janvier","fevrier","mars","avril","mai","juin","juillet",
			"aout","septembre","octobre","novembre","decembre"
		]

		index = months.index(slugify(name)) + 1
		return index

	def saveGardeList2(self,content,save=False):

		# parser = argparse.ArgumentParser(description='Analyseur de fichier des tours de garde',usage="%(prog)s [options]")

		# parser.add_argument('file',type=str, help='fichier source à analyser')
		# parser.add_argument('--save', action="store_true", help='enregistre le tout en base de données')
		# args = parser.parse_args()
		result = {"logs":[],"status":False}
		period_title:str = None

		#with open(args.file,encoding="utf8") as file:
		
		lines = content.split("\n")

		title_pattern = r"SEMAINE DU (?P<start_day_name>\w+) (?P<start_day_number>\d{1,2}) (?P<start_month_name>\w+) (?P<start_year>\d{4}) AU (?P<end_day_name>\w+) (?P<end_day_number>\d{1,2}) (?P<end_month_name>\w+) (?P<end_year>\d{4})"
		
		location_pattern = r"^\[(?P<location>.+?)\]"

		period_id = None
		currentLocation = None
		locations = []

		for i,line in enumerate(lines):

			if len(line.strip()) == 0:
				continue

			if i == 0:
				tt = re.search(title_pattern,line,re.I)
				period_title = line

				if tt:
					start_day_name = tt.group("start_day_name")
					start_day_number = tt.group("start_day_number")
					start_month_name = tt.group("start_month_name")
					start_year = tt.group("start_year")
					end_day_name = tt.group("end_day_name")
					end_day_number = tt.group("end_day_number")
					end_month_name = tt.group("end_month_name")
					end_year = tt.group("end_year")

					# enregistrement de la periode
					slug = slugify(line)

					isExists = db.garde_period.find_one({
						"slug":slug
					})

					if isExists is not None:
						raise Exception('La periode "{}" existe deja'.format(line))

					if save:

						period_id = db.garde_period.insert_one({
							"title":line,
							"slug":slug,
							"start":datetime.datetime(int(start_year),self.get_month_number(start_month_name),int(start_day_number)),
							"end":datetime.datetime(int(end_year),self.get_month_number(end_month_name),int(end_day_number)),
							"is_active":False,
							"create_at":datetime.datetime.utcnow()
						}).inserted_id

					continue
			else:

				if save:
					if period_id is None:
						raise Exception("La periode n'a pas été détectée")

				tt = re.search(location_pattern,line,re.I)
				if tt:
					currentLocation = tt.group("location")
					if currentLocation.upper() in ["II PLATEAUX","II PLATEAU"]:
						currentLocation = "2 PLATEAUX"
					
					currentLocation = currentLocation.lower().title()

					for loc in currentLocation.split("/"):
						locations.append(loc.strip())

					continue
				else:
					items = line.split("/")
					if len(items) != 4:
						raise Exception('Le format "{}" n\'est pas correct. [LIGNE]: {}'.format(line,i+1))

					if not save:
						continue;

					name = items[0].strip().upper().replace("PHCIE","PHARMACIE")
					owner = items[1].upper()
					address = items[3].strip().lower()
					contacts = []

					for tel in items[2].split("-"):
						contacts.append(tel.strip())

					contacts = "-".join(contacts)

					cur_loc = currentLocation.replace('/', '-')
					locality_ =  [ee.strip() for ee in cur_loc.split("-") if len(ee.strip())]

					if len(locality_) > 1:
						for ee in locality_:
							# if ee not in localities:
							ee = re.sub(r"([ ]+)",r" ",ee)
							zone = self.get_zone(ee)

							payload = {
								"garde_period_id":period_id,
								"zone":zone,
								"locality":ee,
								"locality_slug":slugify(ee),
								"pharmacy":name,
								"name":name,
								"pharmacy_slug":slugify(name),
								"slug":slugify(name),
								"owner":owner,
								"contacts":contacts.split('-'),
								"address":address,
								"create_at":datetime.datetime.utcnow()
							}

							db.garde.insert_one(payload)
							self.addOfficialPharmacy(payload,db)
					else:
						# if cur_loc not in localities:
						cur_loc = re.sub(r"([ ]+)",r" ",cur_loc)
						zone = self.get_zone(cur_loc)
						payload = {
							"garde_period_id":period_id,
							"zone":zone,
							"locality":cur_loc,
							"locality_slug":slugify(cur_loc),
							"pharmacy":name,
							"name":name,
							"pharmacy_slug":slugify(name),
							"slug":slugify(name),
							"owner":owner,
							"contacts":contacts.split('-'),
							"address":address,
							"create_at":datetime.datetime.utcnow()
						}
						db.garde.insert_one(payload)
						self.addOfficialPharmacy(payload,db)
							
			
		result["logs"].append("Félicitation le fichier est bien formatté")

		if  save:
			result["logs"].append("Enregistré avec succes")

		result["logs"].append(period_title)
		result["logs"].append(", ".join(sorted(locations)))

		return result["logs"]

		

	def saveGardeList(self):

		# active_period = db.garde_period.find_one({
		# 	"is_active":True
		# })


		date = datetime.date.today()
		r = requests.get(self.gardeUrl,headers={"User-Agent":self.user_agent})
		
		if r.status_code == 200:

			html = re.sub(r"document\.write\('",r"",str(r.text));
			html = re.sub(r"'\);",r"",html);
			html = BeautifulSoup(html,"lxml")

			currentLocation = None
			period = None

			start_day_name = None
			start_day_number = None
			start_month_name = None
			start_year = None
			end_day_name = None
			end_day_number = None
			end_month_name = None
			end_year = None
			period_id = None

			localities = []

			for i,tag in enumerate(html.body):

				if isinstance(tag, NavigableString):
					continue

				tag_class = tag['class']

				if len(tag_class) > 0:

					if "boxTitre" not in tag_class and "boxHphamM" not in tag_class:
						continue

					if "boxTitre" in tag_class:
						currentLocation = tag.get_text().strip().upper()
						if i == 0:
							period = currentLocation

							pattern = r"SEMAINE DU (?P<start_day_name>\w+) (?P<start_day_number>\d{1,2}) (?P<start_month_name>\w+) (?P<start_year>\d{4}) AU (?P<end_day_name>\w+) (?P<end_day_number>\d{1,2}) (?P<end_month_name>\w+) (?P<end_year>\d{4})"

							tt = re.search(pattern,period,re.I)
							

							start_day_name = tt.group("start_day_name")
							start_day_number = tt.group("start_day_number")
							start_month_name = tt.group("start_month_name")
							start_year = tt.group("start_year")
							end_day_name = tt.group("end_day_name")
							end_day_number = tt.group("end_day_number")
							end_month_name = tt.group("end_month_name")
							end_year = tt.group("end_year")

							# enregistrement de la periode
							slug = slugify(period)

							isExists = db.garde_period.find_one({
								"slug":slug,
								"is_active":True,
							})

							if isExists is not None:
								return

							db.garde_period.update_many({
								"is_active":True
							},{
								"$set":{
									"is_active":False
								}
							})

							def get_month_number(name):
								months = [
									"janvier","fevrier","mars","avril","mai","juin","juillet",
									"aout","septembre","octobre","novembre","decembre"
								]

								index = months.index(slugify(name)) + 1
								return index

							period_id = db.garde_period.insert_one({
								"title":period,
								"slug":slug,
								"start":datetime.datetime(int(start_year),get_month_number(start_month_name),int(start_day_number)),
								"end":datetime.datetime(int(end_year),get_month_number(end_month_name),int(end_day_number)),
								"is_active":True
							}).inserted_id

							# print("\n\n")
							# print((" {} ".format(currentLocation)).center(100,"*"))
							# print("\n\n")
						else:
							pass
							# print((" {} ".format(currentLocation)).center(100,"-"))
							# print("\n")



					elif "boxHphamM" in tag_class:
						pharma_page = tag.find("a").get("href").strip(" \r\n")
						name = tag.find("span",class_="boxTpharm").get_text().strip(" \r\n").upper()
						box = tag.find("div",class_="boxBottomS")
						owner = box.find("h3").get_text().strip(" \r\n").upper()
						contacts = []
						pharma_page = "https://www.abidjan.net/sante/pharmacies/"+pharma_page

						for rrr in box.find("h4").contents:
							if not isinstance(rrr, NavigableString):
								continue

							tel = rrr.string.strip()

							if tel.startswith("Tel") and len(tel) > 6:
								contacts.append(tel)

						contacts = " - ".join(contacts)

						if currentLocation.upper() == "II PLATEAU":
							currentLocation = "2 PLATEAUX"


						cur_loc = currentLocation.replace('/', '-').lower().title()
						locality_ =  [ee.strip() for ee in cur_loc.split("-") if len(ee.strip())]
						if len(locality_) > 1:
							for ee in locality_:
								# if ee not in localities:
								ee = re.sub(r"([ ]+)",r" ",ee)
								zone = self.get_zone(ee)

								payload = {
									"garde_period_id":period_id,
									"zone":zone,
									"locality":ee,
									"locality_slug":slugify(ee),
									"pharmacy":name,
									"name":name,
									"pharmacy_slug":slugify(name),
									"slug":slugify(name),
									"owner":owner,
									"contacts":contacts.split('-'),
									"page_url":pharma_page,
									"address":None
								}

								db.garde.insert_one(payload)
								self.addOfficialPharmacy(payload,db)
						else:
							# if cur_loc not in localities:
							cur_loc = re.sub(r"([ ]+)",r" ",cur_loc)
							zone = self.get_zone(cur_loc)
							payload = {
								"garde_period_id":period_id,
								"zone":zone,
								"locality":cur_loc,
								"locality_slug":slugify(cur_loc),
								"pharmacy":name,
								"name":name,
								"pharmacy_slug":slugify(name),
								"slug":slugify(name),
								"owner":owner,
								"contacts":contacts.split('-'),
								"page_url":pharma_page,
								"address":None
							}
							db.garde.insert_one(payload)
							self.addOfficialPharmacy(payload,db)
					

			print("- Remplissage de la base de donnée [OK]")

			logging.info("Remplissage de la base de donnée avec un nouveau tour de garde [Terminé]")

			# thread = Thread(target=self.saveWitSample)
			# thread.start()


	def trainPharmaName(self,value:str):

		if "(" in value:
			value = value[:value.index("(")].strip()

		value = value.replace("saint ","st ").lower()
		value = value.replace("sainte ","ste ").lower()

		print('\r\n Entrainement pharmaName "{}" términé [START]'.format(value))

		texts = [
			"ou est-ce que je peux trouver la ",
			"quelle est la situation geographique de la ",
			"trouve moi stp la localisation de la ",
			"situation geographique de la ",
			"trouve moi la ",
			"recherche moi la ",
			"a quel endroit se trouve la ",
			"ou chercher la ",
			"quelle est la geolocalisation de la ",
			"comment retrouver la ",
			"ou puis-je trouver la ",
			"ou est-ce que je peux trouver la "
		]

		_params = {"v":"20170307"}
		_headers = {
			"Authorization":os.environ["FB_WIT_AUTHORIZATION"],
			"content-type":"application/json",
			"User-Agent":self.user_agent
		}
		_payload = []

		for text in texts:
			start = len(text)
			item = [{
				"text":text+value,
				"entities":[
					{
						"entity":"intent",
						"value":"getPharmaGarde"
					},
					{
						"entity":"pharmaName",
						"start":start,
						"end":start + len(value),
						"value":value
					}
				]
			}]
			
			r = requests.post("https://api.wit.ai/samples?v=20170307", params=_params, headers=_headers, data=json.dumps(item))

			print(r.status_code)

		print('\r\n Entrainement pharmaName "{}" términé [OK]'.format(value))


	def saveWitSample(self):

		"""
		Enregistrement automatique des noms des pharmacies sur wit.ai
		"""



		date = datetime.date.today()
		csv_filename:str = "gardedocs/{}{}{}.csv".format(date.day,date.month,date.year)


		current_date = datetime.datetime(date.year,date.month,date.day)
		# isExists = db.garde_period.find_one({
		# 	"is_active":True,
		# 	"start":{"$lte":current_date},
		# 	"end":{"$gte":current_date},
		# })

		# if isExists is None:
		# 	self.saveGardeList()


		stages = [
			{
				"$lookup":{
					"from":"garde_period",
					"localField":"garde_period_id",
					"foreignField":"_id",
					"as":"period"
				}
			},
			{"$match":{"period.is_active":True}},
			{"$sort":{"pharmacy":1}}
		]

		r = db.garde.aggregate(stages)

		for row in r:
			counter = 0
			#start = time.time()
			value = row["pharmacy"].lower().title()
			self.trainPharmaName(value)
			# elapsedTime = time.time() - start
			# counter = counter + 1

			# if elapsedTime >= 50:  
			# 	print("- Entrainement [PAUSE]")
			# 	time.sleep(15)
			# 	start = time.time()


		print('\r\n Entrainement pharmaName [OK]'.format(value))


if __name__ == "__main__":
	updater:OfficineUpdater = OfficineUpdater()
	#updater.createOfficialPharmacyDB()
	#updater.saveWitSample()
	#updater.saveGardeList()
	logging.info("recherche nouvelle période de tour de garde [en cours]")
	if updater.checkNewGardePeriod():
		logging.info("nouvelle période de tour de garde disponible")
		updater.saveGardeList()
	else:
		logging.info("pas de nouvelle période de tour de garde disponible")



	logging.info("recherche nouvelle période de tour de garde [Terminé]")

	print("- Terminé ")
