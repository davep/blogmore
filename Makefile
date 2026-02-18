app      := blogmore
src      := src/
reports  := .reports
run      := uv run
sync     := uv sync --group dev --group test
build    := uv build
publish  := uv publish --username=__token__ --keyring-provider=subprocess
python   := $(run) python
ruff     := $(run) ruff
lint     := $(ruff) check
fmt      := $(ruff) format
mypy     := $(run) mypy
spell    := $(run) codespell
test     := $(run) pytest --verbose --cov
coverage := $(test) --cov-report html:$(reports)/html
mkdocs   := $(run) mkdocs

##############################################################################
# Setup/update packages the system requires.
.PHONY: ready
ready:				# Make the development environment ready to go
	$(sync)

.PHONY: setup
setup: ready			# Set up the repository for development
	$(run) pre-commit install

.PHONY: update
update:				# Update all dependencies
	$(sync) --upgrade

.PHONY: resetup
resetup: realclean		# Recreate the virtual environment from scratch
	make setup

##############################################################################
# Checking/testing/linting/etc.
.PHONY: test
test:				# Run the test suite
	$(test)

.PHONY: test-verbose
test-verbose:			# Run tests with verbose output
	$(test) -v

.PHONY: coverage
coverage:			# Produce a test coverage report
	$(coverage)
	open $(reports)/html/index.html

.PHONY: test-watch
test-watch:			# Run tests in watch mode
	$(test) -f

.PHONY: lint
lint:				# Check the code for linting issues
	$(lint) $(src)

.PHONY: codestyle
codestyle:			# Is the code formatted correctly?
	$(fmt) --check $(src)

.PHONY: typecheck
typecheck:			# Perform static type checks with mypy
	$(mypy) --scripts-are-modules $(src)

.PHONY: stricttypecheck
stricttypecheck:	        # Perform a strict static type checks with mypy
	$(mypy) --scripts-are-modules --strict $(src)

.PHONY: spellcheck
spellcheck:			# Spell check the code
	$(spell) *.md $(src)

.PHONY: checkall
checkall: spellcheck codestyle lint stricttypecheck test # Check all the things

##############################################################################
# Documentation.
.PHONY: docs
docs:                           # Generate the system documentation
	$(mkdocs) build

.PHONY: rtfm
rtfm:                           # Locally read the library documentation
	$(mkdocs) serve --livereload

.PHONY: publishdocs
publishdocs:			# Set up the docs for publishing
	$(mkdocs) gh-deploy

##############################################################################
# Package/publish.
.PHONY: package
package:			# Package the library
	$(build)

.PHONY: spackage
spackage:			# Create a source package for the library
	$(build) --sdist

.PHONY: testdist
testdist: package			# Perform a test distribution
	$(publish) --index testpypi

.PHONY: dist
dist: package			# Upload to pypi
	$(publish)

##############################################################################
# Utility.
.PHONY: repl
repl:				# Start a Python REPL in the venv.
	$(python)

.PHONY: delint
delint:			# Fix linting issues.
	$(lint) --fix  $(src)

.PHONY: pep8ify
pep8ify:			# Reformat the code to be as PEP8 as possible.
	$(fmt) $(src)

.PHONY: tidy
tidy: pep8ify delint		# Tidy up the code, fixing lint and format issues.

.PHONY: clean-packaging
clean-packaging:		# Clean the package building files
	rm -rf dist

.PHONY: clean
clean: clean-packaging # Clean the build directories
	rm -rf output $(reports)

.PHONY: realclean
realclean: clean		# Clean the venv and build directories
	rm -rf .venv

.PHONY: help
help:				# Display this help
	@grep -Eh "^[a-z]+:.+# " $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.+# "}; {printf "%-20s %s\n", $$1, $$2}'

##############################################################################
# Housekeeping tasks.
.PHONY: housekeeping
housekeeping:			# Perform some git housekeeping
	git fsck
	git gc --aggressive
	git remote update --prune

### Makefile ends here
