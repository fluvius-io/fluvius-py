import '.justcmd/_entry.just'
import '.justcmd/python.just'

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

run-updatedb:
	python tests/fluvius_worker/update_db.py

doc:
	docpress serve

proto:
	protoc -I=./proto/src --python_out=./src/fluvius/domain/proto "./proto/src/_common.proto"
	protoc -I=./proto/src --python_out=./src/fluvius/domain/proto "./proto/src/command.proto"
	protoc -I=./proto/src --python_out=./src/fluvius/domain/proto "./proto/src/event.proto"
	protoc -I=./proto/src --python_out=./src/fluvius/domain/proto "./proto/src/context.proto"
	protoc -I=./proto/src --python_out=./src/fluvius/domain/proto "./proto/src/profile.proto"
	protoc -I=./proto/src --python_out=./src/fluvius/domain/proto "./proto/src/request.proto"
	protoc -I=./proto/src --python_out=./src/fluvius/domain/proto "./proto/src/response.proto"
