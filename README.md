Scrape the NASA JPL tours and notify if a reservation can be made.

> https://www.jpl.nasa.gov/events/tours/


## Development

### Requirements

* [Python 3.8](https://www.python.org/downloads/) or newer,
  and Pip

### Virtual Environment Setup

Dependencies are handled by [Poetry](https://python-poetry.org/), and configured in `pyproject.toml`.

Common Bash commands:

* Install Poetry
  * `pip install poetry`

* Configure Poetry to place the virtualenv folder in the project folder
  (created in a `.venv` folder)
  * `poetry config virtualenvs.in-project true`

* Create a new virtualenv
  * `poetry env use python`

* Use the virtuelenv in the same shell
  * `source $(poetry env info --path)/bin/activate`
  * `deactivate`

* Install dependencies
  (the current project is installed in editable mode by default)
  * `poetry install`

* Add a new dependency
  * `poetry add <package> [--group dev]`

* Remove an existing dependency
  * `poetry remove <package> [--group dev]`

* Update installed packages (and lockfile)
  * `poetry update`

### Code Formatting

Code formatting is handled by [Black](https://black.readthedocs.io/en/stable/).

To auto-format, run:
```bash
black [--check --diff] [--config pyproject.toml] .
```

### Code Linting

Due to the lack of automated testing, the codebase heavily relies on static code checking.
Type hints are used to help the code checkers and IDEs.

General code verification is handled by [Ruff](https://docs.astral.sh/ruff/)
and strict type checking is handled by [mypy](https://mypy.readthedocs.io/en/stable/).

To check the code, run:
```bash
ruff check [--no-cache] [--config pyproject.toml] . && mypy .
```

Some issues can be automatically fixed using the `--fix` flag.


## Deployment

### Version Bumping

Use Poetry's commands to change the package version number (in `pyproject.toml`):

```bash
poetry version [major|minor|patch|<string>]
```

### Packaging

To build a release wheel, run:
```bash
poetry build --format wheel
```
