.PHONY: status validate test check

status:
	python3 scripts/novel_project.py status

validate:
	python3 scripts/novel_project.py validate

test:
	python3 -m unittest discover -s tests -v

check: validate test
