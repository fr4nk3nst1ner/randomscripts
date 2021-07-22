#!/usr/bin/env python

#this is a tamper script that should be used to attempt to bypass refresh tokens.
#it works by auto updating the refresh token as they change. Should be good for JWT, ASPX 
#macos: /usr/local/Cellar/sqlmap/1.5.5/libexec/tamper/<file>
#kali: /usr/share/sqlmap/tamper/<file>


import requests

from lib.core.compat import xrange
from lib.core.enums import PRIORITY

refresh_token = ""
__priority__ = PRIORITY.NORMAL 

def dependencies():
	pass

def getNewToken():
	headers = {"Cookie":"<COOKIE>"}
	data = {"grant_type":"refresh_token",
	"refresh_token":refresh_token}
	url = "https://<URL>/<PATH>"
	resp = requests.post(url=url, headers=headers,data=data)
	print("Token has been Refreshed!")
	return resp.json()['access_token']

def tamper(payload, **kwargs):
	done = False
	while not done:
		try:
			access_token = getNewToken()
			hdrs = kwargs.get("headers",{})
			hdrs["Authorization"] = "Bearer "+access_token
			break
		except:
			pass

	return payload
