.PHONY: install run test

install:
	pip install -e '.[dev]'

run:
	python -m worker.main

test:
	pytest
