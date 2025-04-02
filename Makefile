clear:
	rm -rf dist

build:
	poetry build

publish: clear build
	twine upload -r pypi dist/*
