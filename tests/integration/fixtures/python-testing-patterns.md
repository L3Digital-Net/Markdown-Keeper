---
title: Python Testing Patterns and Best Practices
tags: python,testing,pytest
category: development
concepts: pytest,unittest,mock,fixtures,coverage
---

## Structuring Tests with pytest Fixtures

A well-organized test suite starts with fixtures that eliminate duplication without hiding intent. Define fixtures in `conftest.py` at the appropriate scope: session-level for expensive resources like database connections, function-level for mutable state that must reset between tests.

```python
@pytest.fixture
def db_connection(tmp_path):
    conn = sqlite3.connect(tmp_path / "test.db")
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    yield conn
    conn.close()
```

Fixture finalization (the code after `yield`) handles teardown automatically, even when a test fails. This pattern replaces the `setUp`/`tearDown` ceremony from `unittest.TestCase` with something more composable. Fixtures can depend on other fixtures, forming a dependency graph that pytest resolves at runtime.

For shared test data, prefer factory fixtures over static values. A `make_user` fixture that accepts overrides is more flexible than a `sample_user` fixture returning a frozen dict. See the [pytest fixtures documentation](https://docs.pytest.org/en/stable/how-to/fixtures.html) for advanced scoping patterns.

## Parametrize, Mocking, and Test Organization

`@pytest.mark.parametrize` turns one test function into many. Use it whenever you are testing the same behavior across different inputs rather than writing near-identical test methods.

```python
@pytest.mark.parametrize("input_val,expected", [
    ("hello", 5),
    ("", 0),
    ("café", 4),
])
def test_string_length(input_val, expected):
    assert len(input_val) == expected
```

Mocking with `unittest.mock` requires discipline. Patch at the call site, not at the definition. If `module_a.py` imports `requests.get`, you patch `module_a.requests.get`, not `requests.get` globally. The `autospec=True` flag catches signature mismatches early, which prevents mocks from silently accepting arguments the real implementation would reject.

```python
with patch("myapp.client.requests.get", autospec=True) as mock_get:
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"id": 1}
    result = fetch_user(1)
    mock_get.assert_called_once_with("https://api.example.com/users/1")
```

Organize test files to mirror the source tree. If your project has `src/myapp/parser.py`, the test lives at `tests/test_parser.py` (or `tests/myapp/test_parser.py` for larger projects). Group related assertions into a single test method when they verify one logical behavior; split them when they test independent conditions.

## Coverage Reporting and Practical Thresholds

Coverage is a useful signal, not a target. Running `pytest --cov=myapp --cov-report=term-missing` highlights untested code paths, but chasing 100% coverage often produces low-value tests that assert implementation details rather than behavior.

A practical baseline is 80% line coverage for business logic, with explicit exclusions for protocol boilerplate (CLI entry points, logging setup). Configure these in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["myapp"]
omit = ["myapp/__main__.py"]

[tool.coverage.report]
fail_under = 80
```

Branch coverage (`--cov-branch`) catches missed conditional paths that line coverage alone misses. Combine it with mutation testing tools like [mutmut](https://mutmut.readthedocs.io/) for deeper confidence, though mutation testing is typically reserved for critical paths due to its runtime cost.

For related patterns on structuring integration tests, see [ci-pipeline-best-practices](./ci-pipeline-best-practices.md).
