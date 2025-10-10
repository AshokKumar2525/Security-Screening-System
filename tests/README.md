# Running Unit Tests

To run the automated unit tests for this project:

1. Make sure you have all development dependencies installed (see requirements.txt).
2. From the project root, run:

```
python -m unittest discover tests
```

Or, if you have pytest installed:

```
pytest tests/
```

This will automatically find and run all test files in the `tests/` directory.

If you add new tests, make sure they are named with the `test_*.py` pattern.
