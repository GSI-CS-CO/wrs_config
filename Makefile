SWITCHES ?= switches.json

all:
	python3 do_generate_config.py $(SWITCHES)
	python do_update_params.py

clean:
	rm -rf output || true

prod:
	yes "password" | python3 do_generate_config.py prod_switches.json

verify_v8:
	@$(MAKE) clean
	@$(MAKE) all
	@./tools/compare_dot-configs.sh

Makefile: prereq-rule

prereq-rule::
	git submodule sync
	git submodule init
	git submodule update --recursive
