#!/usr/bin/env python3
"""Measure test ownership and direct production-module references without plugins."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "mousse_controler"
TESTS = ROOT / "tests"
LAYERS = ("unit", "contract", "qualification", "integration", "system")


def _python_files(directory: Path) -> Iterable[Path]:
    return sorted(directory.rglob("test_*.py")) if directory.is_dir() else ()


def _production_references(tree: ast.AST, known: set[str]) -> set[str]:
    references: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "mousse_controler":
                references.update(alias.name for alias in node.names if alias.name in known)
            elif module.startswith("mousse_controler."):
                name = module.split(".", 1)[1].split(".", 1)[0]
                if name in known:
                    references.add(name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("mousse_controler."):
                    name = alias.name.split(".", 1)[1].split(".", 1)[0]
                    if name in known:
                        references.add(name)
    return references


def measure() -> dict[str, object]:
    modules = {
        path.stem for path in SOURCE.glob("*.py") if path.stem != "__init__"
    }
    references: dict[str, list[str]] = {name: [] for name in sorted(modules)}
    cases_by_layer: dict[str, int] = {}
    files_by_layer: dict[str, int] = {}
    source_read_calls = 0
    sleep_calls = 0
    short_polling_sleep_calls = 0
    assertion_calls = 0

    for layer in LAYERS:
        files = tuple(_python_files(TESTS / layer))
        files_by_layer[layer] = len(files)
        cases = 0
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relative = path.relative_to(ROOT).as_posix()
            for name in _production_references(tree, modules):
                references[name].append(relative)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cases += int(node.name.startswith("test_"))
                if not isinstance(node, ast.Call):
                    continue
                function = node.func
                if isinstance(function, ast.Attribute):
                    source_read_calls += int(function.attr == "read_text")
                    assertion_calls += int(function.attr.startswith("assert"))
                    sleep_calls += int(
                        function.attr == "sleep"
                        and isinstance(function.value, ast.Name)
                        and function.value.id == "time"
                    )
                    if (
                        function.attr == "sleep"
                        and isinstance(function.value, ast.Name)
                        and function.value.id == "time"
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, (int, float))
                        and float(node.args[0].value) <= 0.01
                    ):
                        short_polling_sleep_calls += 1
        cases_by_layer[layer] = cases

    missing = [name for name, owners in references.items() if not owners]
    return {
        "schema": "mousse-test-architecture-v1",
        "production_modules": len(modules),
        "directly_referenced_modules": len(modules) - len(missing),
        "modules_without_direct_test_reference": missing,
        "direct_test_files_by_module": references,
        "test_files_by_layer": files_by_layer,
        "test_cases_by_layer": cases_by_layer,
        "test_cases": sum(cases_by_layer.values()),
        "assertion_calls": assertion_calls,
        "source_read_calls": source_read_calls,
        "time_sleep_calls": sleep_calls,
        "short_polling_sleep_calls": short_polling_sleep_calls,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    result = measure()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "production_modules": result["production_modules"],
        "directly_referenced_modules": result["directly_referenced_modules"],
        "test_cases": result["test_cases"],
        "modules_without_direct_test_reference": result[
            "modules_without_direct_test_reference"
        ],
    }, indent=2, ensure_ascii=False))
    return 1 if (
        result["modules_without_direct_test_reference"]
        or result["short_polling_sleep_calls"]
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
