# sql-to-dbt

An agent that migrates legacy SQL Server stored procedures to dbt models, and **proves each migration correct**. It runs the original procedure and the new model on the same data, compares the outputs row by row, and debugs and retries when they differ.

On the bundled 50-procedure corpus: **47 of 50 migrated and verified equivalent; 3 need a human, with the reason and a reviewed proposal for each.** About 2,900 rows were compared across 4 datasets, and a full run costs about $0.05 in Claude Haiku calls.

## How it works

```
T-SQL proc ──► triage ──► Claude translates ──► dbt model
                 │                                  │
                 │        SQL Server runs proc      │  DuckDB runs model
                 │        on 4 datasets × params    │  on the same data
                 │                 └──── row-by-row diff ───┘
                 │                          │
                 │              match ──► verified
                 │              differ ──► diff fed back, retry (max 3)
                 ▼
     needs human (dynamic SQL, nondeterminism, writes to source tables, ...)
     + agent proposal: model, assumptions, reviewer questions
```

- **Ground truth is the legacy database itself.** Procedures run in a real SQL Server (Docker), so T-SQL semantics are the real ones, not a model's guess: case-insensitive collation, `ISNULL` truncation, integer division, cursor NULL propagation.
- **Four datasets per procedure:** a base dataset, two random seeds, and an edge-case set (NULLs, trailing spaces, empty strings, ties, boundary values, orphan rows, year rollover). A translation must match on all of them. On the corpus, the edge set exposed 8 hand-written translations that had passed on a single dataset.
- **Exact comparison:** rows are compared as multisets, so duplicate counts matter. Numeric values within a relative 1e-6 count as equal, and strings ignore trailing spaces as SQL Server does.
- **Parameters:** a parameterized procedure becomes one parameter-free model plus a row filter (`CustomerID = @CustomerID`), checked for every parameter set. When parameters change what gets aggregated, as in date-range reports, the agent switches to dbt vars.
- **Triage:** dynamic SQL, nondeterminism, writes to source tables, OUTPUT parameters and multiple result sets are flagged for a human. The agent still drafts a proposal, verified as far as the blocker allows.
- **Sandboxed:** generated SQL runs in DuckDB with file and network access off, after a guard that allows only a single SELECT.

## Quick start

Requires Docker, [uv](https://docs.astral.sh/uv/) and an Anthropic API key.

```bash
docker compose up -d                       # SQL Server 2022 Developer (legacy side)
uv sync
cp .env.example .env                       # then put your ANTHROPIC_API_KEY in .env

uv run python run_all.py                   # migrate + verify the 50-proc corpus
uv run python dashboard.py                 # dashboard.html
uv run python export.py                    # standalone dbt project in out/corpus/
```

`TRANSLATOR=reference` runs offline with the hand-written reference models instead of Claude. `CLAUDE_MODEL` picks the model (default `claude-haiku-5-5`).

## Migrating your own procedures

```
projects/<name>/
  schema.sql                  CREATE TABLE / VIEW DDL (any schemas; FKs and identity OK)
  data.sql                    optional INSERTs; synthesized from the DDL if missing
  procs/*.sql                 one CREATE PROCEDURE per file
  procs/<file>.params.json    optional parameter sets, e.g. [{"@CustomerID": 3}]
```

```bash
uv run python -m harness.intake projects/<name>          # build datasets, parse procs
uv run python run_all.py --project <name>
uv run python dashboard.py --project <name>               # projects/<name>/dashboard.html
uv run python export.py --project <name>                  # out/<name>/
```

See `projects/example/` for a worked example: parameters, a TOP-N procedure with an optional category, a date-range report, a full-refresh table, and a procedure that updates its source.

## Output

`export.py` writes a dbt project and checks it with a full `dbt build`:

- `models/migrated/`: verified models. Each header records what was verified, and `schema.yml` carries the agent's plain-English explanation of the procedure.
- `models/needs_review/`: proposals, disabled until someone signs off.
- `REVIEW.md`: the review queue, giving for each procedure why it needs review, what it does, the reviewer questions, assumptions, and what isn't migrated.
- `MIGRATION_REPORT.md`: the summary.

## Limits

- Equivalence is proven on the test datasets, not for all possible data. Supplying real or representative `data.sql` makes it much stronger. Synthesized data respects types, NOT NULL and foreign keys, but not business rules.
- The target dialect is DuckDB. Moving models to Snowflake or Databricks means changing the dbt adapter and re-verifying any dialect-specific functions.
- Projects share one dbt working folder, so run one project at a time.

## Layout

| Path | What |
|---|---|
| `migrate.py`, `run_all.py` | per-procedure loop: triage, translate, verify, retry |
| `harness/legacy.py` | runs procedures in SQL Server (rolled-back transactions) |
| `harness/dbt_runner.py` | loads DuckDB, runs and compiles dbt, executes sandboxed |
| `harness/diff.py` | multiset row comparison |
| `harness/preflight.py` | static triage |
| `harness/translate.py` | Claude prompt and response parsing |
| `harness/intake.py` | builds a user project: introspection, data synthesis, parameter derivation |
| `corpus/` | 50-procedure corpus specs and the dataset generator |
| `export.py`, `dashboard.py` | dbt project export and HTML dashboard |
