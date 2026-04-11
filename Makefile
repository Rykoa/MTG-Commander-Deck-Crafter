.PHONY: start install

start:  ## Start MTG Deck Builder
	python3 main.py

install:  ## Install dependencies
	pip install -r requirements.txt
