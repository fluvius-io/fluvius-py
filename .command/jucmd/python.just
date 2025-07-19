export PYTHONPATH 	:= "./src:./tests/_lib:./cmd"
export FLUVIUS_CONFIG_FILE := "config.ini"

TEST_FILES 			:= "*"
TEST_LOG_LEVEL  	:= "info"
TEST_PARAMS			:= env("TEST_PARAMS", "")

# Build python package for distribution into ./dist
build:
	uv build

# Run pytests on [TEST_MODULES], stop on first failure, quiet. Example: `just pytest "*"`
test TEST_MODULES="*":
	pytest -x -q \
		--log-cli-level={{TEST_LOG_LEVEL}} \
		--log-level={{TEST_LOG_LEVEL}} \
		--html=temp/tests-report.html \
		--self-contained-html --color=yes \
		{{TEST_PARAMS}} \
		./tests/{{TEST_MODULES}}/test_{{TEST_FILES}}.py

# Run pytests on [TEST_MODULES], all tests, verbose.
test-all TEST_MODULES:
	@pytest -v \
		--log-cli-level={{TEST_LOG_LEVEL}} \
		--log-level={{TEST_LOG_LEVEL}} \
		--html=temp/tests-report.html \
		--self-contained-html \
		./tests/{{TEST_MODULES}}/test_{{TEST_FILES}}.py

