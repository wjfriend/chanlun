.PHONY: verify verify-full lint typecheck test-critical test-full clean install

# 默认 target
verify: lint typecheck

verify-full: lint typecheck test-critical

lint:
	ruff check .

lint-fix:
	ruff check --fix .

typecheck:
	pyright

test-critical:
	pytest tests/ -m "not slow" -v

test-full:
	pytest tests/ -v

test-cover:
	pytest --cov=. --cov-report=term-missing

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# alias
check: verify
fix: lint-fix