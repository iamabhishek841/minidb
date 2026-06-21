"""
Executor: takes the AST produced by sql_parser.parse_sql() and runs it
against a Database (storage.py).

This is the "query execution engine" piece -- it decides, per statement,
whether it can use an index (fast path) or must fall back to a full
table scan (slow path), and applies WHERE-clause filtering.
"""

from .storage import Database, SchemaError

_COMPARATORS = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
}


def _row_matches(row, condition):
    if condition is None:
        return True
    if condition["op"] == "AND":
        return all(_row_matches(row, c) for c in condition["conditions"])
    col, op, val = condition["column"], condition["op"], condition["value"]
    if col not in row:
        raise SchemaError(f"Unknown column '{col}' in WHERE clause")
    return _COMPARATORS[op](row[col], val)


class Executor:
    def __init__(self, db: Database = None):
        self.db = db or Database()

    def execute(self, ast: dict):
        handler = getattr(self, f"_exec_{ast['type']}", None)
        if handler is None:
            raise SchemaError(f"No executor for statement type {ast['type']}")
        return handler(ast)

    def run(self, sql: str):
        from .sql_parser import parse_sql
        return self.execute(parse_sql(sql))

    # ---------------- statement handlers ----------------
    def _exec_CREATE_TABLE(self, ast):
        self.db.create_table(ast["table"], ast["columns"], ast["primary_key"])
        return f"Table '{ast['table']}' created."

    def _exec_CREATE_INDEX(self, ast):
        table = self.db.get_table(ast["table"])
        table.create_index(ast["column"])
        return f"Index created on {ast['table']}.{ast['column']}."

    def _exec_INSERT(self, ast):
        table = self.db.get_table(ast["table"])
        table.insert(ast["row"])
        return "1 row inserted."

    def _exec_SELECT(self, ast):
        table = self.db.get_table(ast["table"])
        where = ast["where"]

        # --- Fast path: WHERE pk = <value> uses the B-Tree index directly ---
        if where and where.get("op") == "=" and where["column"] == table.primary_key:
            row = table.get_by_pk(where["value"])
            rows = [row] if row else []
        # --- Fast-ish path: WHERE pk > / < / >= / <= uses a B-Tree range scan ---
        elif where and where.get("column") == table.primary_key and where["op"] in (
            "<", "<=", ">", ">="
        ):
            low, high = None, None
            if where["op"] in (">", ">="):
                low = where["value"]
            else:
                high = where["value"]
            rows = [row for _, row in table.index.range_query(low, high)
                    if _row_matches(row, where)]
        else:
            # Slow path: full table scan, filter row by row. O(n).
            rows = [row for row in table.scan() if _row_matches(row, where)]

        if ast["columns"] != ["*"]:
            rows = [{c: row[c] for c in ast["columns"]} for row in rows]
        return rows

    def _exec_UPDATE(self, ast):
        table = self.db.get_table(ast["table"])
        rows = [row for row in table.scan() if _row_matches(row, ast["where"])]
        count = 0
        for row in rows:
            table.update_by_pk(row[table.primary_key], ast["updates"])
            count += 1
        return f"{count} row(s) updated."

    def _exec_DELETE(self, ast):
        table = self.db.get_table(ast["table"])
        rows = [row for row in table.scan() if _row_matches(row, ast["where"])]
        count = 0
        for row in rows:
            table.delete_by_pk(row[table.primary_key])
            count += 1
        return f"{count} row(s) deleted."
