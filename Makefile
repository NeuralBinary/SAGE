.PHONY: install test lint security performance verify run docker clean
install:
	python -m pip install -e '.[dev]'
test:
	pytest -q
lint:
	ruff check src tests scripts
security:
	python scripts/security_check.py
performance:
	PYTHONPATH=src python scripts/performance_check.py --iterations 200
	PYTHONPATH=src python -m sage_plugin.qualification --profile-encode --profile-iterations 30 --max-query-count 40
clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache src/*.egg-info build dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
verify:
	python scripts/security_check.py
	python scripts/architecture_check.py
	python scripts/invariant_check.py
	PYTHONPATH=src python scripts/generate_specs.py --check
	PYTHONPATH=src python scripts/generate_protocol_artifacts.py --check
	PYTHONPATH=src python -m sage_plugin.conformance --json
	python scripts/conformance_matrix.py
	PYTHONPATH=src python scripts/differential_fuzz.py --iterations 250
	PYTHONPATH=src python scripts/chaos_suite.py
	pytest -q
	PYTHONPATH=src python scripts/performance_check.py --iterations 200
	PYTHONPATH=src python -m sage_plugin.qualification --profile-encode --profile-iterations 30 --max-query-count 40
	python -m compileall -q src tests scripts
	$(MAKE) clean
	python scripts/release_check.py
run:
	uvicorn sage_plugin.main:app --reload --port 8080
docker:
	docker compose up --build
