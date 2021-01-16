lint:
	pre-commit run --hook-stage manual --all-files

test:
	pytest

clean:
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -exec rm -r {} \+ -o -type d -name '.pytest_cache' -exec rm -r {} \+ -o -type d -name dist -exec rm -r {} \+
