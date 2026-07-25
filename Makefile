.PHONY: validate test demo check

validate:
	python3 scripts/stg.py validate-repo .

test:
	python3 -m unittest discover -s tests -v

demo:
	python3 scripts/stg.py demo .

check: validate test demo
