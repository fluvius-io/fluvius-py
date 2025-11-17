import '.command/jucmd/_default.just'
import '.command/jucmd/python.just'
import '.command/jucmd/release.just'

help:
	just --list --list-submodules

run-worker:
	python tests/fluvius_worker/run_worker.py

run-cqrs-worker:
	python tests/fluvius_worker/run_cqrs.py

run-cqrs-client:
	python tests/fluvius_worker/run_cqrs_client.py

run-client:
	python tests/fluvius_worker/run_client.py

run MODULE:
	python -m {{MODULE}}

run-updatedb:
	python tests/fluvius_worker/update_db.py

run-fetcher:
	python -m fluvius.dmap.cli.fetcher --config tests/_conf/mock_data_with_manager.yml

run-prober:
	python -m fluvius.dmap.cli.prober --config tests/_conf/mock_data_with_manager.yml --output tests/_conf/mock_data_prober.yml

doc:
	docpress serve

dev:
	#!/usr/bin/env bash
	echo "Start watching for changes in [./src:./tests] ..."
	fswatch ./src ./tests | while read -r file; do
	  echo "Detected change in $file..."
	  sleep 1
	  just test riparius
	  while read -t 1 -r; do :; done  # drain remaining events
	done

recreate-schema MODULE:
	./manager db drop-schema --force "{{MODULE}}"
	./manager db create-schema "{{MODULE}}"

create-schema MODULE:
	./manager db create-schema "{{MODULE}}"

drop-schema MODULE:
	./manager db drop-schema "{{MODULE}}"
	
