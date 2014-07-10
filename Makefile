test:
	python manage.py test django_transfer

verify:
	pyflakes django_transfer
	pep8 --exclude=migrations --ignore=E501,E225 django_transfer

install:
	python setup.py install

publish:
	python setup.py register
	python setup.py sdist upload
