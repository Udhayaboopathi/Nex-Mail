up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose up -d --build

logs:
	docker compose logs -f backend

logs-traefik:
	docker compose logs -f traefik

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python seed.py
