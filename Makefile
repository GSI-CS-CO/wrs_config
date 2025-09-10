SWITCHES ?= switches.json

all:
	python3 do_generate_config.py $(SWITCHES)
	python do_create_copy.py
	python do_convert_v70_to_v80.py

clean:
	rm -rf output || true

prod:
	yes "password" | python3 do_generate_config.py prod_switches.json

Makefile: prereq-rule

prereq-rule::
	git submodule sync
	git submodule init
	git submodule update --recursive
