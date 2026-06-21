# MiniDB -- A Tiny In-Memory SQL Engine

[![tests](https://github.com/iamabhishek841/minidb/actions/workflows/tests.yml/badge.svg)](https://github.com/iamabhishek841/minidb/actions/workflows/tests.yml)

MiniDB is a small in-memory database engine built from scratch in Python.
It implements its own **B-Tree storage index**, a **SQL tokenizer +
recursive-descent parser**, and a **query executor** -- no external
database libraries, no SQLite, no ORM.

This project was built to deeply understand how databases actually work
under the hood: indexing, query planning, and parsing.

## Why build this?

Most CRUD apps just call `sqlite3` or an ORM and never think about *how*
a `WHERE` clause turns into something fast. This project answers that:

- How do you store rows so that point lookups are O(log n) instead of O(n)?
- How do you turn a SQL string into something a program can execute?
- How do you decide whether a query can use an index, or has to scan
  the whole table?

## Architecture

```
            SQL string
                │
                ▼
        ┌───────────────┐
        │   Tokenizer    │  sql_parser.py: tokenize()
        └───────────────┘
                │  tokens
                ▼
        ┌───────────────┐
        │     Parser     │  sql_parser.py: Parser (recursive descent)
        └───────────────┘
                │  AST (dict)
                ▼
        ┌───────────────┐
        │    Executor    │  executor.py: walks AST, picks fast/slow path
        └───────────────┘
                │
                ▼
        ┌───────────────┐
        │  Storage (Table)│ storage.py: rows indexed by primary key
        └───────────────┘
                │
                ▼
        ┌───────────────┐
        │     B-Tree     │  btree.py: sorted index, O(log n) ops
        └───────────────┘
```

## Components

### 1. B-Tree (`btree.py`)
A from-scratch order-`t` B-Tree (CLRS-style) used as the primary index
for every table. Supports:
- `insert(key, value)` -- O(log n)
- `search(key)` -- O(log n)
- `range_query(low, high)` -- O(log n + k), used for `WHERE pk > X`
- `delete(key)` -- O(log n) (simplified: no node merging/rebalancing
  after deletion, documented as a known limitation -- a full
  CLRS delete with merge/borrow is a natural extension)

A plain Python `dict` would give O(1) point lookups but can't answer
range queries without a full scan. The B-Tree keeps keys sorted across
nodes, so both point and range lookups stay fast.

### 2. Storage (`storage.py`)
- `Table`: holds the schema, the primary-key B-Tree index, and optional
  secondary indexes (hash-based) on other columns.
- `Database`: a collection of named tables.

### 3. SQL Parser (`sql_parser.py`)
Two stages:
- **Tokenizer**: regex-based lexer that turns SQL text into a token stream
  (keywords, identifiers, numbers, strings, operators).
- **Parser**: hand-written recursive-descent parser that turns tokens
  into an AST (plain nested dicts). One method per statement type
  (`CREATE TABLE`, `INSERT`, `SELECT`, `UPDATE`, `DELETE`, `CREATE INDEX`).

### 4. Executor (`executor.py`)
Walks the AST and decides the execution strategy:
- `WHERE pk = X` &rarr; **B-Tree point lookup**, O(log n)
- `WHERE pk > / < / >= / <= X` &rarr; **B-Tree range scan**, O(log n + k)
- anything else &rarr; **full table scan** with row-by-row filtering, O(n)

## Supported SQL

```sql
CREATE TABLE users (id INT, name TEXT, age INT) PRIMARY KEY (id)
CREATE INDEX ON users (age)
INSERT INTO users (id, name, age) VALUES (1, 'Alice', 30)
SELECT * FROM users
SELECT name, age FROM users WHERE age > 25
SELECT * FROM users WHERE age > 20 AND age < 40
UPDATE users SET age = 31 WHERE id = 1
DELETE FROM users WHERE id = 1
```

## Running it

```bash
# Interactive shell
python repl.py

# Run tests
python tests/test_btree.py
python tests/test_database.py
```

## Known limitations (intentional scope cuts)

- No JOINs, subqueries, GROUP BY, or ORDER BY (would be natural next steps)
- B-Tree delete doesn't rebalance/merge underflowed nodes -- correctness
  is preserved, but the tree can become unbalanced after many deletes
- Single-threaded, no persistence (everything is in-memory) -- could be
  extended with WAL-style logging or pickling to disk
- No transaction/concurrency support

## What this demonstrates

- Implementing a non-trivial data structure (B-Tree) from scratch and
  reasoning about its time complexity
- Writing a tokenizer + recursive-descent parser for a real grammar
- Designing a query executor that picks different execution strategies
  based on the query shape (index lookup vs. range scan vs. full scan)
- Test-driven verification of correctness for both the data structure
  and the end-to-end SQL pipeline
