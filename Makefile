all:
	python3 do_generate_config.py switches.json

clean:
	rm -rf output || true

prod:
	yes "password" | python3 do_generate_config.py prod_switches.json

test:
	yes "password" | python3 do_generate_config.py switches.json

calibration_v8:
	python do_convert_v70_to_v80.py

Makefile: prereq-rule

prereq-rule::
	git submodule sync
	git submodule init
	git submodule update --recursive
