.PHONY: install test lint security performance verify run docker
install:
	python -m pip install -e '.[dev]'
test:
	pytest -q
lint:
	ruff check src tests scripts
security:
	python scripts/security_check.py
performance:
	python scripts/performance_check.py --iterations 200
verify:
	pytest -q
	python scripts/security_check.py
	python -m sage_plugin.conformance --json
	python scripts/performance_check.py --iterations 200
	python -m compileall -q src tests scripts
run:
	uvicorn sage_plugin.main:app --reload --port 8080
docker:
	docker compose up --build
