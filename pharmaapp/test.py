#!/usr/bin/python3.7
# -*- coding:utf-8 -*-


# from bs4 import BeautifulSoup
# from bs4.element import NavigableString

# import requests
# import re
# import datetime
# import os
# import csv

# r = requests.get("https://www.abidjan.net/inc/abidjan/inc_pharmacie.js")
# date = datetime.date.today()
# csv_filename:str = "gardedocs/{}{}{}-test.csv".format(date.day,date.month,date.year)

# if r.status_code == 200:

# 	html = re.sub(r"document\.write\('",r"",str(r.text));
# 	html = re.sub(r"'\);",r"",html);
# 	html = BeautifulSoup(html,"lxml")

# 	currentLocation = None
# 	period = None

# 	start_day_name = None
# 	start_day_number = None
# 	start_month_name = None
# 	start_year = None
# 	end_day_name = None
# 	end_day_number = None
# 	end_month_name = None
# 	end_year = None

# 	for i,tag in enumerate(html.body):

# 		if isinstance(tag, NavigableString):
# 			continue

# 		tag_class = tag['class']

# 		if len(tag_class) > 0:

# 			if "boxTitre" not in tag_class and "boxHphamM" not in tag_class:
# 				continue

# 			if "boxTitre" in tag_class:
# 				currentLocation = tag.get_text().strip().upper()
# 				if i == 0:
# 					period = currentLocation

# 					pattern = r"SEMAINE DU (?P<start_day_name>\w+) (?P<start_day_number>\d{1,2}) (?P<start_month_name>\w+) (?P<start_year>\d{4}) AU (?P<end_day_name>\w+) (?P<end_day_number>\d{1,2}) (?P<end_month_name>\w+) (?P<end_year>\d{4})"

# 					tt = re.search(pattern,period,re.I)
					

# 					start_day_name = tt.group("start_day_name")
# 					start_day_number = tt.group("start_day_number")
# 					start_month_name = tt.group("start_month_name")
# 					start_year = tt.group("start_year")
# 					end_day_name = tt.group("end_day_name")
# 					end_day_number = tt.group("end_day_number")
# 					end_month_name = tt.group("end_month_name")
# 					end_year = tt.group("end_year")
					

# 					# print("\n\n")
# 					# print((" {} ".format(currentLocation)).center(100,"*"))
# 					# print("\n\n")
# 				else:
# 					pass
# 					# print((" {} ".format(currentLocation)).center(100,"-"))
# 					# print("\n")



# 			elif "boxHphamM" in tag_class:
# 				pharma_page = tag.find("a").get("href").strip(" \r\n")
# 				name = tag.find("span",class_="boxTpharm").get_text().strip(" \r\n").upper()
# 				box = tag.find("div",class_="boxBottomS")
# 				owner = box.find("h3").get_text().strip(" \r\n").upper()
# 				contacts = []
# 				situation = ""

# 				for rrr in box.find("h4").contents:
# 					if not isinstance(rrr, NavigableString):
# 						continue

# 					tel = rrr.string.strip()

# 					if tel.startswith("Tel") and len(tel) > 6:
# 						contacts.append(tel)

# 				contacts = " - ".join(contacts)

# 				value = "{};{};{};{};{};{};{};{};{};{};{};{};{}".format(period,start_day_name,start_day_number,start_month_name,start_year,end_day_name,end_day_number,end_month_name,end_year,currentLocation,name,owner,contacts)

# 				#print(value)
# 				pharma_page = "https://www.abidjan.net/sante/pharmacies/"+pharma_page

# 				rr = requests.get(pharma_page)
# 				if rr.status_code == 200:
# 					html2 = BeautifulSoup(rr.text,"lxml")
# 					container = html2.find("div",id="module")
# 					box2 = container.find("div",class_="boxBottomS2")

# 					for rrr in box2.find("h4").contents:
# 						if not isinstance(rrr, NavigableString):
# 							continue

# 						situation = rrr.string.strip()

# 						if situation.startswith("Direction") and len(situation) > 12:
# 							situation = situation[11:]
# 							break

				


