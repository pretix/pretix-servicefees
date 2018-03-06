all: localecompile

localecompile:
	django-admin compilemessages

localegen:
	django-admin makemessages --keep-pot -a -i build -i dist -i "*egg*" --settings pretix.settings

