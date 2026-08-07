.PHONY: install test coverage typecheck lint security performance openclaw verify run docker quickstart release clean
install:
	python -m pip install -e '.[dev]'
test:
	pytest -q
coverage:
	pytest -q --cov=sage_plugin --cov-report=term-missing --cov-fail-under=80
typecheck:
	mypy src/sage_plugin
lint:
	ruff check src tests scripts
security:
	python scripts/security_check.py
openclaw:
	cd integrations/openclaw && npm install --ignore-scripts && npm run check && npm run build && npm run tck
performance:
	PYTHONPATH=src python scripts/performance_check.py --iterations 200
	PYTHONPATH=src python -m sage_plugin.qualification --profile-encode --profile-iterations 30 --max-query-count 40
clean:
	rm -rf .coverage .pytest_cache .ruff_cache .mypy_cache src/*.egg-info build dist integrations/openclaw/node_modules integrations/openclaw/package-lock.json integrations/openclaw/dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
verify:
	$(MAKE) openclaw
	python scripts/security_check.py
	python scripts/architecture_check.py
	python scripts/invariant_check.py
	PYTHONPATH=src python scripts/generate_specs.py --check
	PYTHONPATH=src python scripts/generate_protocol_artifacts.py --check
	PYTHONPATH=src python -m sage_plugin.conformance --json
	python scripts/conformance_matrix.py
	node scripts/openclaw_adapter_check.mjs
	PYTHONPATH=src python scripts/differential_fuzz.py --iterations 250
	PYTHONPATH=src python scripts/chaos_suite.py
	$(MAKE) typecheck
	$(MAKE) coverage
	PYTHONPATH=src python scripts/performance_check.py --iterations 200
	PYTHONPATH=src python -m sage_plugin.qualification --profile-encode --profile-iterations 30 --max-query-count 40
	python -m compileall -q src tests scripts
	$(MAKE) clean
	python scripts/release_check.py
run:
	uvicorn sage_plugin.main:app --reload --port 8080
docker:
	docker compose -f docker-compose.yml up --build
quickstart:
	./quickstart.sh
release: openclaw
	python scripts/build_release.py --output dist
	python scripts/package_check.py --source dist/sage-plugin-v0.2.7.zip --wheel dist/sage_agent_protocol-0.2.7-py3-none-any.whl --hermes dist/sage-hermes-plugin-v0.2.7.zip --openclaw dist/sage-agent-openclaw-sage-0.2.7.tgz
