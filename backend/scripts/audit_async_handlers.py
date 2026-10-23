"""Liste (ou convertit) les handlers `async def` de routes/ qui ne contiennent aucun `await`.
Usage: python scripts/audit_async_handlers.py [--fix]
"""
import ast
import os
import sys

ROUTES = os.path.join(os.path.dirname(__file__), "..", "routes")


def has_await(node):
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Await, ast.AsyncFor, ast.AsyncWith)):
            return True
    return False


def is_route(node):
    for d in node.decorator_list:
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in ("get", "post", "put", "patch", "delete"):
            return True
    return False


def main(fix=False):
    total = 0
    for fn in sorted(os.listdir(ROUTES)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(ROUTES, fn)
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
        targets = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and is_route(n) and not has_await(n)]
        if not targets:
            continue
        total += len(targets)
        print(f"{fn}: {len(targets)} handler(s) async sans await -> {', '.join(n.name for n in targets)}")
        if fix:
            lines = src.splitlines(keepends=True)
            for n in targets:
                line = lines[n.lineno - 1]
                assert "async def " in line, (fn, n.name)
                lines[n.lineno - 1] = line.replace("async def ", "def ", 1)
            open(path, "w", encoding="utf-8").write("".join(lines))
    print(f"Total: {total}{' (convertis en def)' if fix else ''}")


if __name__ == "__main__":
    main(fix="--fix" in sys.argv)
