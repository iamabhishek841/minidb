"""
A small SQL parser supporting a useful subset:

  CREATE TABLE users (id INT, name TEXT, age INT) PRIMARY KEY (id)
  CREATE INDEX ON users (age)
  INSERT INTO users (id, name, age) VALUES (1, 'Alice', 30)
  SELECT * FROM users
  SELECT name, age FROM users WHERE age > 25
  SELECT * FROM users WHERE age > 20 AND age < 40
  UPDATE users SET age = 31 WHERE id = 1
  DELETE FROM users WHERE id = 1

Design: classic two-stage parser.
  1. Tokenizer (lexer): turns the raw SQL string into a flat list of
     tokens (keywords, identifiers, numbers, strings, operators, punctuation).
  2. Parser: a recursive-descent parser that consumes tokens left to
     right and builds a small AST (plain dicts/namedtuples) describing
     the statement. The executor (executor.py) walks this AST.

This is intentionally minimal -- no joins, no subqueries, no GROUP BY.
The point is to demonstrate parsing + tree-walking, not to rebuild Postgres.
"""

import re
from collections import namedtuple

TOKEN_SPEC = [
    ("STRING",   r"'[^']*'"),
    ("NUMBER",   r"\d+(\.\d+)?"),
    ("OP",       r"<=|>=|!=|=|<|>|\(|\)|,|\*"),
    ("WORD",     r"[A-Za-z_][A-Za-z0-9_]*"),
    ("SKIP",     r"\s+"),
]
TOKEN_RE = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC))

KEYWORDS = {
    "CREATE", "TABLE", "INDEX", "ON", "PRIMARY", "KEY", "INSERT", "INTO",
    "VALUES", "SELECT", "FROM", "WHERE", "AND", "OR", "UPDATE", "SET",
    "DELETE", "INT", "TEXT", "FLOAT", "BOOL",
}

Token = namedtuple("Token", ["type", "value"])


class SQLSyntaxError(Exception):
    pass


def tokenize(sql: str):
    tokens = []
    pos = 0
    while pos < len(sql):
        m = TOKEN_RE.match(sql, pos)
        if not m:
            raise SQLSyntaxError(f"Unexpected character at: {sql[pos:pos+10]!r}")
        kind = m.lastgroup
        text = m.group()
        pos = m.end()
        if kind == "SKIP":
            continue
        if kind == "WORD" and text.upper() in KEYWORDS:
            tokens.append(Token(text.upper(), text.upper()))
        elif kind == "WORD":
            tokens.append(Token("IDENT", text))
        elif kind == "STRING":
            tokens.append(Token("STRING", text[1:-1]))
        elif kind == "NUMBER":
            tokens.append(Token("NUMBER", float(text) if "." in text else int(text)))
        else:  # OP
            tokens.append(Token(text, text))
    tokens.append(Token("EOF", None))
    return tokens


class Parser:
    """Recursive-descent parser. Each statement type has its own method."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, type_):
        tok = self.advance()
        if tok.type != type_:
            raise SQLSyntaxError(f"Expected {type_}, got {tok.type} ({tok.value!r})")
        return tok

    def parse(self):
        tok = self.peek()
        if tok.type == "CREATE":
            return self.parse_create()
        if tok.type == "INSERT":
            return self.parse_insert()
        if tok.type == "SELECT":
            return self.parse_select()
        if tok.type == "UPDATE":
            return self.parse_update()
        if tok.type == "DELETE":
            return self.parse_delete()
        raise SQLSyntaxError(f"Unknown statement starting with {tok.type}")

    # ---------------- CREATE TABLE / CREATE INDEX ----------------
    def parse_create(self):
        self.expect("CREATE")
        nxt = self.peek()
        if nxt.type == "TABLE":
            return self._parse_create_table()
        if nxt.type == "INDEX":
            return self._parse_create_index()
        raise SQLSyntaxError("Expected TABLE or INDEX after CREATE")

    def _parse_create_table(self):
        self.expect("TABLE")
        table_name = self.expect("IDENT").value
        self.expect("(")
        columns = {}
        while True:
            col_name = self.expect("IDENT").value
            col_type_tok = self.advance()
            type_map = {"INT": int, "FLOAT": float, "TEXT": str, "BOOL": bool}
            if col_type_tok.type not in type_map:
                raise SQLSyntaxError(f"Unknown column type {col_type_tok.type}")
            columns[col_name] = type_map[col_type_tok.type]
            if self.peek().type == ",":
                self.advance()
                continue
            break
        self.expect(")")
        primary_key = None
        if self.peek().type == "PRIMARY":
            self.advance()
            self.expect("KEY")
            self.expect("(")
            primary_key = self.expect("IDENT").value
            self.expect(")")
        else:
            primary_key = next(iter(columns))  # default: first column
        return {
            "type": "CREATE_TABLE",
            "table": table_name,
            "columns": columns,
            "primary_key": primary_key,
        }

    def _parse_create_index(self):
        self.expect("INDEX")
        self.expect("ON")
        table_name = self.expect("IDENT").value
        self.expect("(")
        column = self.expect("IDENT").value
        self.expect(")")
        return {"type": "CREATE_INDEX", "table": table_name, "column": column}

    # ---------------- INSERT ----------------
    def parse_insert(self):
        self.expect("INSERT")
        self.expect("INTO")
        table_name = self.expect("IDENT").value
        self.expect("(")
        cols = [self.expect("IDENT").value]
        while self.peek().type == ",":
            self.advance()
            cols.append(self.expect("IDENT").value)
        self.expect(")")
        self.expect("VALUES")
        self.expect("(")
        vals = [self._parse_literal()]
        while self.peek().type == ",":
            self.advance()
            vals.append(self._parse_literal())
        self.expect(")")
        return {
            "type": "INSERT",
            "table": table_name,
            "row": dict(zip(cols, vals)),
        }

    def _parse_literal(self):
        tok = self.advance()
        if tok.type in ("NUMBER", "STRING"):
            return tok.value
        raise SQLSyntaxError(f"Expected literal, got {tok.type}")

    # ---------------- SELECT ----------------
    def parse_select(self):
        self.expect("SELECT")
        cols = ["*"] if self.peek().type == "*" and self._consume_star() else self._parse_col_list()
        self.expect("FROM")
        table_name = self.expect("IDENT").value
        where = None
        if self.peek().type == "WHERE":
            self.advance()
            where = self._parse_condition()
        return {
            "type": "SELECT",
            "table": table_name,
            "columns": cols,
            "where": where,
        }

    def _consume_star(self):
        self.advance()
        return True

    def _parse_col_list(self):
        cols = [self.expect("IDENT").value]
        while self.peek().type == ",":
            self.advance()
            cols.append(self.expect("IDENT").value)
        return cols

    # ---------------- WHERE clause: simple AND-chain of comparisons ----------------
    def _parse_condition(self):
        conditions = [self._parse_comparison()]
        while self.peek().type == "AND":
            self.advance()
            conditions.append(self._parse_comparison())
        return {"op": "AND", "conditions": conditions} if len(conditions) > 1 else conditions[0]

    def _parse_comparison(self):
        col = self.expect("IDENT").value
        op_tok = self.advance()
        if op_tok.type not in ("=", "!=", "<", ">", "<=", ">="):
            raise SQLSyntaxError(f"Expected comparison operator, got {op_tok.type}")
        val = self._parse_literal()
        return {"op": op_tok.type, "column": col, "value": val}

    # ---------------- UPDATE ----------------
    def parse_update(self):
        self.expect("UPDATE")
        table_name = self.expect("IDENT").value
        self.expect("SET")
        updates = {}
        col = self.expect("IDENT").value
        self.expect("=")
        updates[col] = self._parse_literal()
        while self.peek().type == ",":
            self.advance()
            col = self.expect("IDENT").value
            self.expect("=")
            updates[col] = self._parse_literal()
        where = None
        if self.peek().type == "WHERE":
            self.advance()
            where = self._parse_condition()
        return {"type": "UPDATE", "table": table_name, "updates": updates, "where": where}

    # ---------------- DELETE ----------------
    def parse_delete(self):
        self.expect("DELETE")
        self.expect("FROM")
        table_name = self.expect("IDENT").value
        where = None
        if self.peek().type == "WHERE":
            self.advance()
            where = self._parse_condition()
        return {"type": "DELETE", "table": table_name, "where": where}


def parse_sql(sql: str):
    tokens = tokenize(sql)
    return Parser(tokens).parse()
