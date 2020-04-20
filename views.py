#!/usr/bin/python3
# -*-coding:utf-8 -*-
import os 
from pharmaapp.PharmaBot import PharmaBot,app
import logging
logging.basicConfig(level=logging.DEBUG)


def create_app():
	webhook:PharmaBot = PharmaBot(witAccessToken=os.environ["FB_WIT_AUTHORIZATION"])
	return app

# if __name__ == "__main__":
#webhook:PharmaBot = PharmaBot(witAccessToken=os.environ["FB_WIT_AUTHORIZATION"])
	
# 	#print(PharmaBot.fbsend.saveAttachment("https://scontent.fabj3-1.fna.fbcdn.net/v/t1.0-9/s851x315/90520668_507568489884208_6296356488965259264_n.jpg?_nc_cat=111&_nc_sid=8024bb&_nc_eui2=AeEnjloB6cCsIZrJ6ivhE98g-wOkj4fjfNugxWOVpNOHmZ6QePZ2edNoNZF03fP37CMCXj773oNrhNl1TWzccrM5JXKTQC9Exns8THMxIYgYTw&_nc_oc=AQkKJxycpJi2ukUF88aiTSCEXstdQBOPOC7nfe5CWL_p1lXcTZpMLGQW9bSzxRwuHC0&_nc_ht=scontent.fabj3-1.fna&_nc_tp=7&oh=43aecfebb4aa421e0c42033c90d772db&oe=5E9EE64D", asset_type="image"))

# 	webhook.run(debug=True,host='10.0.1.90',port=5000)
# 	#webhook.run(debug=True, host='192.168.1.224', port=5000, ssl_context=('cert.pem', 'key.pem'))
