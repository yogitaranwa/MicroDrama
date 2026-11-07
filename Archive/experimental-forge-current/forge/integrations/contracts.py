"""Dependency-free CLI contract checks from pinned upstream source.

Only argparse declarations are executed. No imports, inference, models or
network calls. This checks actual flags/choices and types, not model quality.
"""
import argparse
import ast
from pathlib import Path


def parser_from_source(source, constants):
    tree = ast.parse(Path(source).read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name in ('_parse_args', 'get_parser'))
    body = []
    for node in fn.body:
        # Keep only ArgumentParser construction and parser.add_argument.
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'parser' for t in node.targets):
            body.append(node)
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == 'parser'
            and node.value.func.attr == 'add_argument'):
            body.append(node)
    body.append(ast.Assign(targets=[ast.Name(id='result', ctx=ast.Store())],
                           value=ast.Name(id='parser', ctx=ast.Load())))
    module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))
    def str2bool(value):
        if value.lower() in ('true', '1', 'yes'): return True
        if value.lower() in ('false', '0', 'no'): return False
        raise argparse.ArgumentTypeError('boolean expected')
    ns = {'argparse': argparse, 'str2bool': str2bool, **constants}
    exec(compile(module, str(source), 'exec'), ns)
    return ns['result']
