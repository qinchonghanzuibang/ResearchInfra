# Development

ResearchInfra supports three common local development workflows:

- **pip/venv** for the standard Python toolchain.
- **uv** for fast virtual environments and installs.
- **conda** for contributors who manage Python with conda or mamba.

Use one workflow per checkout. All workflows install the package in editable
mode so local code changes are reflected immediately.

## pip and venv

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
researchinfra --help
python -m researchinfra --help
python -m pytest
```

If your default `python` is older than 3.10, call a specific interpreter such as
`python3.12`.

## uv

ResearchInfra does not require a checked-in `uv.lock` yet because the package is
still a lightweight library foundation. Use uv for local editable installs:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
uv run researchinfra --help
uv run pytest
```

If you want to run without activating the environment, keep using `uv run`.

## conda

Create an environment from the included `environment.yml`:

```bash
conda env create -f environment.yml
conda activate researchinfra
researchinfra --help
python -m pytest
```

`mamba env create -f environment.yml` should work as a faster drop-in
alternative when mamba is available.

The conda environment uses Python 3.12, installs `pip`, and then installs
ResearchInfra in editable mode with the `dev` optional dependency group.

## Common Commands

You can run commands directly:

```bash
python -m pytest
python -m ruff check .
python -m ruff format .
python -m build
```

Or use the Makefile:

```bash
make install
make install-dev
make test
make lint
make format
make clean
```

The Makefile uses `PYTHON ?= python`. Activate your environment first, or pass
an interpreter explicitly, for example `make PYTHON=.venv/bin/python test`.

## Test Workflow

Run the full test suite before committing:

```bash
python -m pytest
```

Smoke-test the CLI and workspace initializer:

```bash
researchinfra --help
python -m researchinfra --help
researchinfra init /tmp/researchinfra-smoke
```

The smoke workspace is local output and should not be committed.

## Formatting and Linting

Ruff is the only quality tool in the v1 developer setup. It handles linting,
import sorting, and formatting while keeping dependencies small:

```bash
python -m ruff check .
python -m ruff format .
```

Run `python -m ruff check --fix .` to apply safe lint fixes.

Static type checking with mypy is future work. The package is typed and ships
`py.typed`, but the project does not yet enforce a mypy gate in CI.

## Troubleshooting

If editable installation fails because your Python is too old, use Python 3.10
or newer. Python 3.12 is recommended for local development.

If `researchinfra` is not found after installation, confirm that your virtual
environment is active or run the command through the interpreter:

```bash
python -m researchinfra --help
```

If build isolation tries to download packages in a restricted environment, use a
network-enabled environment or preinstall the build requirements from
`pyproject.toml`.
