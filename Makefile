all:
	python do_generate_config.py switches.json

clean:
	rm -rf output || true

test:
	yes "password" | python do_generate_config.py switches.json

Makefile: prereq-rule

prereq-rule::
	git submodule sync
	git submodule init
	git submodule update --recursive
