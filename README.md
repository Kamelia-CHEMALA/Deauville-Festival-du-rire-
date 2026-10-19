# Deauville Festival du Rire — Festival Management Platform

**ECE Paris · Object-Oriented Programming in Python · 2026–2027**

A Python application for managing the **Deauville Festival du Rire (10–13 June 2027)**. It provides a command-line interface (CLI), a FastAPI JSON API, a public website and an administration interface. Organisers can manage artists and performances while the application enforces scheduling and capacity rules.

## Requirements

- Python (the project environment is managed by `uv`)
- [`uv`](https://docs.astral.sh/uv/)
- Git, to clone the repository

Commands below are run **from the repository root**. The web pages and default JSON file are loaded using paths relative to this directory.

## Install

1. Download the project as a ZIP file.
2. Extract the ZIP file.
3. Open the extracted folder in VS Code.
4. Open a terminal in the project folder.
5. Install the dependencies:

   ```bash
   uv sync

## Run the command-line application

```bash
uv run deauville
uv run deauville venues
uv run deauville programme 2027-06-11
uv run deauville artist <ARTIST-SLUG>
uv run deauville now 2027-06-11T20:00
uv run deauville add
uv run deauville cancel <PERFORMANCE-ID>
```

The `add` command interactively creates a **solo show**. The `cancel` command removes an existing performance. Use the API or admin interface for the other supported operations.

To work with a separate JSON file, add `--data` and its path, for example:

```bash
uv run deauville --data data/festival-test.json programme 2027-06-11
```

**Caution:** Admin actions and the `add`/`cancel` CLI commands save changes to the selected JSON file. To preserve the original dataset, work on a copy.

## Run the web server

```bash
uv run deauville serve
```

Open:

- Public website: <http://127.0.0.1:8000/>
- Administration interface: <http://127.0.0.1:8000/admin/>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

The server uses the default `data/festival.json` file, or the file specified with `--data`.

## API overview

The full API contract is documented in [`API.md`](API.md). Main routes include:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/festival` | Festival dates and information |
| GET | `/api/venues` | Venues and capacities |
| GET | `/api/artists` | Artists |
| GET | `/api/artists/{artist_slug}` | Artist and their performances |
| GET | `/api/programme` | Programme; optional `day` and `venue` filters |
| GET | `/api/now` | Currently running and next performances; optional `at` |
| GET | `/api/performances/{performance_id}` | Performance details |
| POST | `/api/artists` | Create an artist |
| POST | `/api/performances` | Schedule a performance |
| PUT | `/api/performances/{performance_id}` | Move or update a performance |
| DELETE | `/api/performances/{performance_id}` | Cancel a performance |
| POST | `/api/performances/{performance_id}/participants` | Register for a workshop |

## Tests, formatting and build

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv build
```

During development, use `uv run ruff format .` to apply formatting. The test suite includes API contract tests and exercises. The last local run reported **57 passing tests**; rerun the commands above to verify your checkout.

On a Windows machine where application-control policy blocks the isolated build environment, the following **local workaround** succeeded:

```bash
uv build --no-build-isolation
```

This workaround requires the build backend to be installed in the active environment. It does **not** replace verification that `uv build` works on a fresh machine.

## Project structure

```text
src/deauville/
  festival.py       Domain classes and business rules
  storage.py        Abstract storage interface and JSON implementation
  api.py            FastAPI routes, request models and HTTP responses
  cli.py            Command-line commands and server entry point
  __init__.py       Python package marker
web/
  public/           Public festival website
  admin/            Administration interface
data/
  festival.json     Default festival data
  festival-test.json Additional sample/test data
tests/             API contract and project tests
B1/ ... B5/         Learning steps and side exercises
API.md              Detailed HTTP API contract
pyproject.toml      Package configuration and dependencies
uv.lock             Locked dependency versions
```

## Architecture and object-oriented design

- **`Performance`** is an abstract base class for the three types of performances. It defines shared information (title, venue, start, duration) and common behavior such as calculating the end time, festival day and API view.
- **`SoloShow`**, **`Lineup`** and **`Workshop`** inherit from `Performance`. Each implements its own artists, summary and role behavior. `Lineup` enforces a minimum number of distinct acts; `Workshop` manages participants and available places.
- **`Festival`** manages artists and the collection of performances. It validates additions, cancellations and moves. Its methods prevent callers from directly replacing the performance collection.
- **`Storage`** is an abstract interface with `load()` and `save()` methods. **`JsonStorage`** implements this interface using a JSON file.
- **`api.py`** translates HTTP requests into calls on the domain model and storage. **`cli.py`** provides an alternative user interface for the same model.

### Where do the business rules live?

Rules are implemented in **`festival.py`**, rather than duplicated in the CLI or API. They include:

- Performance duration between 1 and 360 minutes.
- Festival-day calculation: a day runs until **06:00 the next morning**.
- Performance dates must fall within the festival period.
- A venue or artist cannot be booked for overlapping performances, with a **30-minute buffer** around shows.
- Lineups require at least two acts; the host cannot also be an act.
- Workshop registration respects capacity and rejects duplicate participant names.

### How are errors reported?

Domain exceptions explain the broken rule:

- `NotFoundError`: a requested venue, artist or performance does not exist.
- `ConflictError`: an existing booking, registration or festival-date constraint prevents the action.
- `InvalidError`: supplied values violate a validation rule.

The API converts these exceptions into HTTP **404**, **409** and **422** responses, respectively. FastAPI also validates malformed request bodies and query parameters. The CLI displays domain error messages in the terminal.

### How could JSON storage be replaced by a database?

Create a new class, such as `SqliteStorage`, implementing the same `Storage.load()` and `Storage.save()` interface. Configure the CLI and `create_app(storage)` to use the new implementation. The `Festival` and `Performance` business rules would not need to change. A production database implementation should additionally consider transactions, concurrent edits and migrations.

## Implemented features and limitations

**Implemented:** festival and venue listings, artist profiles, programme filtering, current/upcoming performances, creation/moving/cancellation of performances, workshop registration, CLI, web pages, JSON persistence, automated tests and package build.

**Current limitations / future improvements:**

- Storage uses a local JSON file, not a database; concurrent writers are not coordinated.
- The CLI's interactive `add` command supports solo shows only; other performance types are managed through the API.
- A SQLite backend is an optional extension and is **not implemented**.
- The fresh-clone installation and standard isolated build still need to be verified on a separate checkout.

No additional application bugs have been confirmed from the available test results. Passing tests do not prove the absence of bugs.

## Learning materials

The repository also retains the course instructions and side exercises in [`B1`](B1/README.md), [`B2`](B2/README.md), [`B3`](B3/README.md), [`B4`](B4/README.md) and [`B5`](B5/README.md).
