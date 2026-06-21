import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from minidb import Executor, SchemaError, SQLSyntaxError


def fresh_executor_with_users():
    ex = Executor()
    ex.run("CREATE TABLE users (id INT, name TEXT, age INT) PRIMARY KEY (id)")
    ex.run("INSERT INTO users (id, name, age) VALUES (1, 'Alice', 30)")
    ex.run("INSERT INTO users (id, name, age) VALUES (2, 'Bob', 25)")
    ex.run("INSERT INTO users (id, name, age) VALUES (3, 'Carol', 40)")
    return ex


def test_create_table_and_insert():
    ex = fresh_executor_with_users()
    rows = ex.run("SELECT * FROM users")
    assert len(rows) == 3


def test_select_with_equality_on_pk_uses_index_path():
    ex = fresh_executor_with_users()
    rows = ex.run("SELECT * FROM users WHERE id = 2")
    assert rows == [{"id": 2, "name": "Bob", "age": 25}]


def test_select_with_range_on_pk():
    ex = fresh_executor_with_users()
    rows = ex.run("SELECT * FROM users WHERE id > 1")
    ids = sorted(r["id"] for r in rows)
    assert ids == [2, 3]


def test_select_with_filter_on_non_pk_column():
    ex = fresh_executor_with_users()
    rows = ex.run("SELECT name FROM users WHERE age > 28")
    names = sorted(r["name"] for r in rows)
    assert names == ["Alice", "Carol"]


def test_select_with_and_condition():
    ex = fresh_executor_with_users()
    rows = ex.run("SELECT * FROM users WHERE age > 20 AND age < 35")
    names = sorted(r["name"] for r in rows)
    assert names == ["Alice", "Bob"]


def test_update():
    ex = fresh_executor_with_users()
    result = ex.run("UPDATE users SET age = 31 WHERE id = 1")
    assert result == "1 row(s) updated."
    row = ex.run("SELECT * FROM users WHERE id = 1")[0]
    assert row["age"] == 31


def test_delete():
    ex = fresh_executor_with_users()
    result = ex.run("DELETE FROM users WHERE id = 2")
    assert result == "1 row(s) deleted."
    rows = ex.run("SELECT * FROM users")
    assert len(rows) == 2
    assert all(r["id"] != 2 for r in rows)


def test_duplicate_primary_key_raises():
    ex = fresh_executor_with_users()
    try:
        ex.run("INSERT INTO users (id, name, age) VALUES (1, 'Dup', 99)")
        assert False, "expected SchemaError"
    except SchemaError:
        pass


def test_secondary_index_creation_does_not_break_queries():
    ex = fresh_executor_with_users()
    ex.run("CREATE INDEX ON users (age)")
    rows = ex.run("SELECT * FROM users WHERE age > 28")
    assert len(rows) == 2


def test_syntax_error_on_garbage_sql():
    ex = Executor()
    try:
        ex.run("SELECT FROM WHERE")
        assert False, "expected SQLSyntaxError"
    except SQLSyntaxError:
        pass


if __name__ == "__main__":
    test_create_table_and_insert()
    test_select_with_equality_on_pk_uses_index_path()
    test_select_with_range_on_pk()
    test_select_with_filter_on_non_pk_column()
    test_select_with_and_condition()
    test_update()
    test_delete()
    test_duplicate_primary_key_raises()
    test_secondary_index_creation_does_not_break_queries()
    test_syntax_error_on_garbage_sql()
    print("All database tests passed.")
