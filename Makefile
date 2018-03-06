all: localecompile

localecompile:
	django-admin compilemessages

localegen:
	django-admin makemessages --keep-pot -l de_Informal -l de -i build -i dist -i "*egg*"

