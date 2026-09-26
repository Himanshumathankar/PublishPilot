.PHONY: dev down logs test lint migrate

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	docker compose run --rm backend pytest
	docker compose run --rm frontend npm test

lint:
	docker compose run --rm backend ruff check app tests
	docker compose run --rm frontend npm run lint

migrate:
	docker compose run --rm backend alembic upgrade head

