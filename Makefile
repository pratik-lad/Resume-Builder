.PHONY: run up down logs test eval fmt pull

pull:
	ollama pull dolphin-llama3

run:
	cd api && uvicorn main:app --reload --port 8000

up:
	docker compose up --build api n8n

up-full:
	docker compose --profile full up --build

down:
	docker compose down

logs:
	docker compose logs -f api

test:
	pytest tests -q

eval:
	python eval/run_eval.py
