"""
Storage layer: Table + Database.

Design:
- Each Table has a schema (column name -> type) and a primary key column.
- Rows are stored once, indexed by primary key in a BTree for O(log n)
  point lookups and range scans.
- A full table scan (for queries on non-indexed columns) iterates the
  BTree's in-order traversal, which is still O(n) but sorted.
- Secondary indexes (optional) are separate BTrees mapping
  column_value -> set of primary keys, giving faster filtering on
  non-PK columns.
"""

from .btree import BTree


class SchemaError(Exception):
    pass


class Table:
    def __init__(self, name, columns, primary_key):
        """
        columns: dict like {"id": int, "name": str, "age": int}
        primary_key: name of the primary key column (must be in columns)
        """
        if primary_key not in columns:
            raise SchemaError(f"Primary key '{primary_key}' not in columns")
        self.name = name
        self.columns = columns
        self.primary_key = primary_key
        self.index = BTree(t=4)          # primary_key -> row (dict)
        self.secondary_indexes = {}      # col_name -> {value: set(pk)}

    def create_index(self, column):
        if column not in self.columns:
            raise SchemaError(f"Unknown column '{column}'")
        idx = {}
        for pk, row in self.index.in_order():
            idx.setdefault(row[column], set()).add(pk)
        self.secondary_indexes[column] = idx

    def insert(self, row: dict):
        for col in self.columns:
            if col not in row:
                raise SchemaError(f"Missing column '{col}' in insert")
        for col in row:
            if col not in self.columns:
                raise SchemaError(f"Unknown column '{col}'")

        pk_value = row[self.primary_key]
        if self.index.search(pk_value) is not None:
            raise SchemaError(
                f"Duplicate primary key '{pk_value}' in table '{self.name}'"
            )
        self.index.insert(pk_value, dict(row))

        for col, idx in self.secondary_indexes.items():
            idx.setdefault(row[col], set()).add(pk_value)

    def get_by_pk(self, pk_value):
        return self.index.search(pk_value)

    def scan(self):
        """Full table scan, sorted by primary key. Returns list of rows."""
        return [row for _, row in self.index.in_order()]

    def delete_by_pk(self, pk_value):
        row = self.index.search(pk_value)
        if row is None:
            return False
        self.index.delete(pk_value)
        for col, idx in self.secondary_indexes.items():
            idx.get(row[col], set()).discard(pk_value)
        return True

    def update_by_pk(self, pk_value, updates: dict):
        row = self.index.search(pk_value)
        if row is None:
            return False
        for col, idx in self.secondary_indexes.items():
            idx.get(row[col], set()).discard(pk_value)
        row.update(updates)
        self.index.insert(pk_value, row)
        for col, idx in self.secondary_indexes.items():
            idx.setdefault(row[col], set()).add(pk_value)
        return True


class Database:
    def __init__(self):
        self.tables = {}

    def create_table(self, name, columns, primary_key):
        if name in self.tables:
            raise SchemaError(f"Table '{name}' already exists")
        self.tables[name] = Table(name, columns, primary_key)
        return self.tables[name]

    def get_table(self, name):
        if name not in self.tables:
            raise SchemaError(f"Table '{name}' does not exist")
        return self.tables[name]

    def drop_table(self, name):
        if name not in self.tables:
            raise SchemaError(f"Table '{name}' does not exist")
        del self.tables[name]
