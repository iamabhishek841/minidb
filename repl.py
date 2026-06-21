"""
Interactive SQL shell for MiniDB.

Usage:
    python repl.py

Type SQL statements terminated by Enter. Type `exit` or `quit` to leave.
"""

from minidb import Executor, SchemaError, SQLSyntaxError


BANNER = """
MiniDB -- a tiny in-memory SQL engine with a B-Tree storage index.
Type SQL statements (no trailing semicolon needed). Type 'exit' to quit.

Example:
  CREATE TABLE users (id INT, name TEXT, age INT) PRIMARY KEY (id)
  INSERT INTO users (id, name, age) VALUES (1, 'Alice', 30)
  INSERT INTO users (id, name, age) VALUES (2, 'Bob', 25)
  SELECT * FROM users WHERE age > 20
"""


def main():
    print(BANNER)
    executor = Executor()
    while True:
        try:
            sql = input("minidb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        if not sql:
            continue
        if sql.lower() in ("exit", "quit"):
            break
        try:
            result = executor.run(sql)
            if isinstance(result, list):
                if not result:
                    print("(0 rows)")
                for row in result:
                    print(row)
            else:
                print(result)
        except (SchemaError, SQLSyntaxError) as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
