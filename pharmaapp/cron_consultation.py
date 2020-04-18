#!/usr/bin/python3
# -*-coding:utf-8 -*-

import pymongo
import datetime,os
from .Consultation import Consultation


DATABASE_URL = os.environ["DATABASE_URL"]
client = pymongo.MongoClient(DATABASE_URL)
db = client.pharma_garde

limit = 20
consultations = db.consultation.find({
	"state":{"$in":[1,4]}
}).limit(limit).sort("_id",1)

# il faut verifier la validitité de cette
# conversation
# si la conversation est inactive depuis 5 minutes
# il faut la fermer

duration = 2*60
for item in consultations:

	now = datetime.datetime.utcnow()
	last_presence = item["last_presence"]

	delta = now - last_presence
	elapsed_time = delta.total_seconds()

	if elapsed_time >= duration:
		consultation = Consultation(data=item)
		consultation.close()

