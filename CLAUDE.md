# CLAUDE.md

## Purpose of this project

This is a **learning project**. The goal is for the user to learn, by writing it themselves:

1. How to implement a threadpool (`include/threadpool.hpp`, `src/threadpool.cpp`)
2. How to implement matrix multiplication, then optimize it with cache blocking and then parallel blocking on top of the threadpool (`include/matmul.hpp`, `src/matmul.cpp`)

## Rules for Claude

### Core learning code: do NOT write it

This covers the implementation of:
- `Threadpool` (constructors, destructor, `enqueue`, `waitAll`, `worker`, synchronization logic)
- `multiplyNaive`, `multiplyBlocked`, `multiplyBlockedParallel`, `multiplyBlock`

For this code:
- Do not write, rewrite, or "fix" the implementation, even partially, and do not paste working snippets of it into replies.
- Only when the user asks, give **hints** that point in the right direction: name the concept, ask a guiding question, point to the line or condition that's wrong, or explain the relevant theory (e.g. spurious wakeups, lost wakeups, loop ordering, cache lines, tile sizing, false sharing).
- Start with the smallest useful hint; go more concrete only if the user asks for more.
- Reviewing the user's code and explaining *why* something is buggy or slow is fine. Handing them the fix is not.

### Everything else: help freely

Go ahead and write or modify:
- Unit tests (`tests/`, GoogleTest)
- Benchmarks and timing harnesses, `src/main.cpp`
- Helpers such as `randomMatrix` and `matricesEqual`
- Build system (`Makefile`), tooling, sanitizer or profiling setup, `.gitignore`, docs

If it's unclear whether something counts as core learning code, ask first.

## Build and test

- Build the app: `make` (outputs `build/app`)
- Run the app: `make run`
- Build and run tests: `make test` (outputs `build/tests`, links GoogleTest via `-lgtest -lgtest_main`)
- Run a subset of tests: `./build/tests --gtest_filter='Suite.*'`
- Clean: `make clean`

Settings: C++17, `g++ -Wall -Wextra -pthread`. `src/main.cpp` is excluded from the test binary because `gtest_main` provides `main()`.

## Conventions

- `Matrix` is dense and row-major: element (r, c) is at `data[r * cols + c]`.
- Public API is documented with `/** ... */` Javadoc-style comments in the headers; keep that style.
- Tests compare floating-point results with `matricesEqual` and a tolerance, not exact equality, because blocked variants sum in a different order.
