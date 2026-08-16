PYTHON ?= python3

.PHONY: install test run seed docker-up docker-down smoke

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	pytest -q

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

seed:
	curl -fsS -X POST 'http://localhost:8000/api/simulate?count=36&seed=7'

docker-up:
	docker compose up --build

docker-down:
	docker compose down

smoke:
	curl -fsS http://localhost:8000/health
	curl -fsS http://localhost:8000/ready
	curl -fsS http://localhost:8000/metrics
