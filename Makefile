all:
	python3 do_generate_config.py switches.json

clean:
	rm -rf output || true

prod:
	yes "password" | python3 do_generate_config.py prod_switches.json

test:
	python3 do_generate_config.py switches_test.json
	python do_create_copy.py
	python do_convert_v70_to_v80.py

v8.x:
	$(MAKE) all
	python do_create_copy.py
	python do_convert_v70_to_v80.py
	grep "CONFIG_DOTCONF_FW_VERSION=\"8.0\"" -rl output/config/ | \
	rsync --no-relative --files-from=- ./ \
	tsl101:/common/usr/timing/wrs_tools/wrs_tn2_configuration/dot-configs/8.x/

Makefile: prereq-rule

prereq-rule::
	git submodule sync
	git submodule init
	git submodule update --recursive
