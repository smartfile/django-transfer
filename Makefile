test:
	python manage.py test django_transfer

install:
	python setup.py install

publish:
	python setup.py register
	python setup.py sdist upload
