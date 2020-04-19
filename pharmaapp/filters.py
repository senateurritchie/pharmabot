from .PharmabotBot import app

@app.template_filter('aaz_shorten')
def aaz_shorten(s,limit:int=50,suffix:str="...",attrs:str=''):
	"""
	limite un texte à un nombre de caractère
	"""
	text = str(s[:limit])

	if len(s) > limit:
		text = text + '&nbsp;<a href="" {}><small>{}</small></a>'.format(attrs,suffix)

	return text



