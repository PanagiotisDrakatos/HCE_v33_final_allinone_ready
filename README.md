# HCE Backtest Engine (hcebt)

A high-performance backtesting engine for market simulations with support for multiple order types, advanced fill models, and persistent storage backends (ClickHouse, TimescaleDB).

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quickstart](#quickstart)
  - [Windows](#windows)
  - [macOS / Linux / WSL](#macos--linux--wsl)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Environment Variables](#environment-variables)
- [Docker](#docker)
- [CI/CD](#cicd)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

## Features

- **Multiple Order Types**: Market, Limit, Stop, Stop-Limit orders with realistic fill simulation
- **Advanced Slippage Models**: Fixed ticks, basis points, percentage of spread, and hybrid models
- **Persistence Backends**: In-memory, ClickHouse, and TimescaleDB support
- **High Performance**: Batch processing with configurable queue management
- **Deterministic Testing**: Seeded RNG for reproducible backtests
- **Comprehensive Testing**: 90%+ test coverage with unit and integration tests

## Prerequisites

- **Python**: 3.11 or higher (tested with 3.12)
- **Git**: For cloning the repository
- **pip**: Python package manager (comes with Python)
- **(Optional) Docker**: For running ClickHouse/TimescaleDB backends

## Quickstart

### Windows

```cmd
# Clone the repository
git clone https://github.com/PanagiotisDrakatos/HCE_v33_final_allinone_ready.git
cd HCE_v33_final_allinone_ready

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest -q -m "not integration"

# Run example backtest
python backtest.py run --config examples/cfg.yaml --ab examples/A.json examples/B.json
```

### macOS / Linux / WSL

```bash
# Clone the repository
git clone https://github.com/PanagiotisDrakatos/HCE_v33_final_allinone_ready.git
cd HCE_v33_final_allinone_ready

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest -q -m "not integration"

# Run example backtest
python backtest.py run --config examples/cfg.yaml --ab examples/A.json examples/B.json
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/PanagiotisDrakatos/HCE_v33_final_allinone_ready.git
cd HCE_v33_final_allinone_ready
```

### 2. Create Virtual Environment

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux/WSL:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install the package in editable mode
pip install -e .

# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 4. Verify Installation

```bash
python -c "import hcebt; print('hcebt installed successfully!')"
pytest -q -m "not integration"
```

## Running the Application

### Command Line Interface

The main entrypoint is `backtest.py`:

```bash
python backtest.py run --config <config_file> --ab <file_A> <file_B>
```

**Example:**
```bash
python backtest.py run --config examples/cfg.yaml --ab examples/A.json examples/B.json
```

### Configuration

Configuration is provided via YAML files. See `examples/cfg.yaml` for a complete example:

```yaml
run_id: demo_run_003
strat_id: breakout_v1
commit_sha: cafe5eed
fill:
  slip_mode: bps          # fixed_ticks|bps|pct_spread|hybrid
  bps: 2.0
  bid_ask_aware: true
  seed: 777
batch:
  backend: none           # none|clickhouse|timescale
  batch_size: 5000
  flush_interval_ms: 500
  queue_max_batches: 200
  clickhouse_url: http://localhost:8123
  timescale_dsn: postgresql://postgres:postgres@localhost:5432/hce
  table: market_signals
```

### Input Data Format

Market data files (A.json, B.json) should be JSON arrays with the following structure:

```json
[
  {
    "ts": 1234567890000,
    "symbol": "BTC-USD",
    "last": 50000.0,
    "bid": 49995.0,
    "ask": 50005.0,
    "vol": 1.5,
    "side": 1,
    "qty": 1.0,
    "type": "market"
  }
]
```

## Testing

### Run All Unit Tests

```bash
pytest -q -m "not integration"
```

### Run With Coverage

```bash
pytest -q -m "not integration" --cov=hcebt --cov=lib --cov-report=term-missing --cov-report=xml
```

### Run Integration Tests

Integration tests require running database backends. Set environment variables to enable:

```bash
# Start databases with Docker (see Docker section)
docker-compose up -d

# Run integration tests
export IT_CLICKHOUSE=1
export IT_TIMESCALE=1
export CLICKHOUSE_URL=http://localhost:8123
export TIMESCALE_DSN=postgresql://postgres:postgres@localhost:5432/hce

pytest -q -m "integration"
```

### Run Specific Tests

```bash
# Run a single test file
pytest tests/test_fills_targeted.py -v

# Run a specific test
pytest tests/test_fills_targeted.py::test_market_fill_basic -v
```

### Fast Testing

For quick validation during development:

```bash
# Windows
scripts\unit_fast.cmd

# Linux/macOS
./scripts/unit_fast.sh
```

## Environment Variables

Copy `.env.example` to `.env` and configure as needed:

```bash
cp .env.example .env
```

### Application Environment Variables

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `HCE_LOG_LEVEL` | Python logging level | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Integration Test Environment Variables

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `IT_CLICKHOUSE` | Enable ClickHouse integration tests | No | `0` | `1` |
| `IT_TIMESCALE` | Enable TimescaleDB integration tests | No | `0` | `1` |
| `CLICKHOUSE_URL` | ClickHouse server URL | No | `http://localhost:8123` | `http://clickhouse:8123` |
| `TIMESCALE_DSN` | TimescaleDB connection string | No | `postgresql://postgres:postgres@localhost:5432/hce` | `postgresql://user:pass@host:5432/db` |

### CI/CD Environment Variables

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `CODECOV_TOKEN` | CodeCov upload token | No (CI only) | - | `abc123...` |
| `GITHUB_TOKEN` | GitHub API token | No (CI only) | Auto-provided by GitHub Actions | `ghp_...` |
| `REVIEWDOG_GITHUB_API_TOKEN` | ReviewDog GitHub API token | No (CI only) | Falls back to `GITHUB_TOKEN` | `ghp_...` |

### Configuration-Based Variables (Not Environment Variables)

The following are configured via YAML config files, not environment variables:

- `clickhouse_url` - Set in `batch.clickhouse_url` config field
- `timescale_dsn` - Set in `batch.timescale_dsn` config field
- Database credentials - Set in `docker-compose.yml` or connection strings

## Docker

The project includes `docker-compose.yml` for running database backends.

### Start All Services

```bash
docker-compose up -d
```

### Start Individual Services

```bash
# ClickHouse only
docker-compose up -d clickhouse

# TimescaleDB only
docker-compose up -d timescaledb
```

### Stop Services

```bash
docker-compose down
```

### View Logs

```bash
docker-compose logs -f
```

### Database Access

**ClickHouse:**
- HTTP Interface: http://localhost:8123
- Native Protocol: localhost:9000
- Default credentials: user=`default`, password=`` (empty)

**TimescaleDB:**
- Host: localhost
- Port: 5432
- Database: `hce`
- User: `postgres`
- Password: `postgres`

### Initialize Databases

Database schemas are automatically initialized from SQL files:
- ClickHouse: `persistence/clickhouse/init.sql`
- TimescaleDB: `persistence/timescale/init.sql`

## CI/CD

### GitHub Actions Workflows

The project uses GitHub Actions for CI/CD. Key workflows:

- **`ci.yml`** - Main CI pipeline: lint, test, coverage
- **`pr-lite.yml`** - Fast PR checks
- **`push-full.yml`** - Full checks on push to main
- **`docker.yml`** - Docker image builds

### Running CI Checks Locally

#### Lint with Ruff

```bash
ruff check .
```

#### Format Check with Black

```bash
black --check .
```

#### Auto-format with Black

```bash
black .
```

#### Run All CI Checks

```bash
# Lint
ruff check .

# Format check
black --check .

# Tests with coverage
pytest -q -m "not integration" --cov=hcebt --cov=lib --cov-report=term-missing --cov-report=xml

# Coverage requirement: 85%
```

### Using Make

Makefile targets for common tasks:

```bash
# Create virtual environment
make venv

# Install dependencies
make install

# Install dev dependencies
make dev

# Run linting
make lint

# Format code
make fmt

# Run tests
make test

# Run all checks
make check
```

### Git Hooks

The project includes pre-push hooks that run linting and tests before allowing pushes:

```bash
# Install hooks
bash install_hooks.sh

# Hooks will automatically run:
# - ruff check
# - black --check
# - pytest

# Bypass hooks if needed (use sparingly)
git push --no-verify
```

### Act (Local GitHub Actions)

Test GitHub Actions workflows locally using [act](https://github.com/nektos/act):

```bash
# Copy example secrets
cp .act.secrets.example .secrets

# Run workflow
act -j lint_and_unit
```

## Troubleshooting

### Common Issues

#### 1. Module Not Found: `hcebt`

**Problem:** `ModuleNotFoundError: No module named 'hcebt'`

**Solution:**
```bash
pip install -e .
```

#### 2. Import Error: `lib` module

**Problem:** Cannot import from `lib` package

**Solution:** The package must be installed in editable mode:
```bash
pip install -e .
```

#### 3. Pytest Not Found

**Problem:** `pytest: command not found`

**Solution:**
```bash
pip install -r requirements.txt
# Or specifically:
pip install pytest pytest-cov
```

#### 4. Tests Failing Due to Coverage

**Problem:** `Required test coverage of 85% not reached`

**Solution:** This is a quality gate. Run with coverage report to identify gaps:
```bash
pytest -q --cov=hcebt --cov=lib --cov-report=term-missing
```

#### 5. ClickHouse/TimescaleDB Connection Errors

**Problem:** Integration tests fail with connection errors

**Solution:**
```bash
# Ensure Docker services are running
docker-compose up -d

# Check service health
docker-compose ps

# View logs for errors
docker-compose logs clickhouse
docker-compose logs timescaledb

# Restart services if needed
docker-compose restart
```

#### 6. Port Already in Use

**Problem:** `Error starting userland proxy: listen tcp 0.0.0.0:5432: bind: address already in use`

**Solution:**
```bash
# Check what's using the port
# Linux/macOS:
lsof -i :5432

# Windows:
netstat -ano | findstr :5432

# Stop conflicting service or change docker-compose.yml ports
```

### Windows-Specific Issues

#### 1. Long Path Issues

**Problem:** File path too long errors

**Solution:**
- Enable long path support in Windows:
  ```cmd
  reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1
  ```
- Or clone to a shorter path like `C:\code\hce`

#### 2. Script Execution Policy

**Problem:** Cannot activate virtual environment

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 3. Line Ending Issues (Git)

**Problem:** Black/Ruff failing on Windows due to CRLF

**Solution:**
```bash
git config core.autocrlf input
git rm --cached -r .
git reset --hard
```

### WSL-Specific Issues

#### 1. Docker Not Available in WSL

**Problem:** Docker commands fail in WSL

**Solution:**
- Install Docker Desktop for Windows
- Enable WSL 2 integration in Docker Desktop settings
- Or use `docker-compose` from Windows: `/mnt/c/Program\ Files/Docker/Docker/resources/bin/docker-compose.exe`

#### 2. Permission Issues

**Problem:** Permission denied errors

**Solution:**
```bash
# Fix file permissions
chmod +x scripts/*.sh
```

### Debugging Tips

#### Enable Debug Logging

```bash
export HCE_LOG_LEVEL=DEBUG
python backtest.py run --config examples/cfg.yaml --ab examples/A.json examples/B.json
```

#### Check Python Environment

```bash
# Verify Python version
python --version

# Verify packages installed
pip list | grep -E "(hcebt|pydantic|numpy|pandas|pytest)"

# Verify import works
python -c "import hcebt; print(hcebt.__file__)"
```

#### Run Single Test with Verbose Output

```bash
pytest tests/test_fills_targeted.py::test_market_fill_basic -vv -s
```

### Getting Help

If you encounter issues not covered here:

1. Check existing GitHub Issues
2. Review GitHub Actions logs for CI failures
3. Enable debug logging: `export HCE_LOG_LEVEL=DEBUG`
4. Open a new issue with:
   - Python version: `python --version`
   - OS and version
   - Full error traceback
   - Steps to reproduce

## Project Structure

```
HCE_v33_final_allinone_ready/
├── hcebt/                  # Main package
│   ├── __init__.py
│   ├── config.py           # Configuration models (Pydantic)
│   ├── fills.py            # Fill simulation models
│   ├── persistence.py      # Database persistence layer
│   └── runner.py           # Main backtest runner
├── lib/                    # Utility libraries
│   ├── kahan.py            # Kahan summation for numerical stability
│   └── timeutil.py         # Time utilities
├── tests/                  # Test suite
│   ├── integration/        # Integration tests (require databases)
│   └── test_*.py           # Unit tests
├── examples/               # Example configurations and data
│   ├── cfg.yaml            # Example config
│   ├── A.json              # Example market data A
│   └── B.json              # Example market data B
├── scripts/                # Helper scripts
├── persistence/            # Database initialization scripts
│   ├── clickhouse/init.sql
│   └── timescale/init.sql
├── .github/                # GitHub Actions workflows
├── backtest.py             # Main CLI entrypoint
├── docker-compose.yml      # Database services
├── pyproject.toml          # Project metadata and tool configs
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Development dependencies
├── pytest.ini              # Pytest configuration
└── README.md               # This file
```

## License

See repository for license information.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and ensure tests pass: `pytest -q`
4. Format code: `black .`
5. Lint code: `ruff check .`
6. Commit changes: `git commit -m "feat: my feature"`
7. Push to branch: `git push origin feature/my-feature`
8. Open a Pull Request

### Code Quality Requirements

- All tests must pass
- Test coverage must be ≥85%
- Code must pass `ruff check`
- Code must pass `black --check`
- Commit messages should follow conventional commits

---

**Happy Backtesting! 🚀**
