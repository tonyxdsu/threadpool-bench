# Compiler
CXX = g++
# -O3 -march=native: full optimization plus every instruction set this CPU supports
# (AVX2/AVX-512, FMA). The binary may not run on other machines.
# -g keeps debug symbols for gdb/perf; it does not slow the code down.
# -falign-loops=64 starts every loop on a 64-byte boundary. Without it, where a hot loop lands
# depends on the size of everything linked before it: the blocked kernel's inner loop ran 25-45%
# slower when it straddled two 64-byte lines, and unrelated code changes could flip that.
OPTFLAGS = -O3 -march=native -g -falign-loops=64
CXXFLAGS = -std=c++17 -Wall -Wextra -Iinclude -pthread $(OPTFLAGS)
# -MMD -MP write a .d file per object listing the headers it includes, so editing a header
# rebuilds everything that uses it. Without this, a benchmark can silently run stale code.
DEPFLAGS = -MMD -MP
TEST_FLAGS = -lgtest -lgtest_main -pthread

# Directories
SRC_DIR = src
TEST_DIR = tests
BENCH_DIR = bench
BUILD_DIR = build

# App files
APP_SRCS = $(wildcard $(SRC_DIR)/*.cpp)
APP_OBJS = $(patsubst $(SRC_DIR)/%.cpp,$(BUILD_DIR)/%.o,$(APP_SRCS))
TARGET = $(BUILD_DIR)/app

# Test files
# Exclude src/main.cpp from tests because gtest_main provides main()
LIB_SRCS = $(filter-out $(SRC_DIR)/main.cpp,$(APP_SRCS))
LIB_OBJS = $(patsubst $(SRC_DIR)/%.cpp,$(BUILD_DIR)/%.o,$(LIB_SRCS))

TEST_SRCS = $(wildcard $(TEST_DIR)/*.cpp)
TEST_OBJS = $(patsubst $(TEST_DIR)/%.cpp,$(BUILD_DIR)/%.test.o,$(TEST_SRCS))
TEST_TARGET = $(BUILD_DIR)/tests

# Benchmark files. Needs Google Benchmark: sudo apt install libbenchmark-dev libbenchmark-tools
# The OpenBLAS reference (bench/openblas_bench.cpp) is built only if OpenBLAS is installed
# (sudo apt install libopenblas-dev). Override with OPENBLAS=0 or OPENBLAS=1.
ifeq ($(origin OPENBLAS),undefined)
OPENBLAS := $(shell pkg-config --exists openblas 2>/dev/null && echo 1 || echo 0)
endif
BENCH_SRCS = $(wildcard $(BENCH_DIR)/*.cpp)
BENCH_CPPFLAGS := $(shell pkg-config --cflags benchmark 2>/dev/null)
BENCH_LIBS := $(shell pkg-config --libs benchmark 2>/dev/null || echo -lbenchmark) -pthread
ifeq ($(OPENBLAS),1)
BENCH_CPPFLAGS += $(shell pkg-config --cflags openblas)
BENCH_LIBS += $(shell pkg-config --libs openblas)
else
BENCH_SRCS := $(filter-out $(BENCH_DIR)/openblas_bench.cpp,$(BENCH_SRCS))
endif
BENCH_OBJS = $(patsubst $(BENCH_DIR)/%.cpp,$(BUILD_DIR)/%.bench.o,$(BENCH_SRCS))
BENCH_TARGET = $(BUILD_DIR)/bench
# Extra linker flags, e.g. -L for a Google Benchmark built from source.
BENCH_LDFLAGS ?=

# Benchmark runs. Results go to bench/results/<LABEL>.json. LABEL defaults to the commit the
# sources came from, plus -dirty if they have uncommitted changes. Set it to name a run:
#   make bench-run LABEL=simd-v1
# ARGS passes extra flags to the benchmark binary, e.g. ARGS=--benchmark_filter=BM_Naive
LABEL ?= $(shell git describe --always --dirty 2>/dev/null || echo unversioned)
RESULTS_DIR = $(BENCH_DIR)/results
PLOTS_DIR = $(BENCH_DIR)/plots
BENCH_REPS ?= 5
BENCH_FLAGS = --benchmark_counters_tabular=true --benchmark_context=git=$(LABEL)
COMPARE_PY ?= /usr/share/benchmark/compare.py

# Stop early, with the install command, if Google Benchmark is missing.
ifneq ($(filter bench bench-run bench-quick,$(MAKECMDGOALS)),)
ifneq ($(shell pkg-config --exists benchmark 2>/dev/null && echo yes),yes)
$(error Google Benchmark not found. Install it with: sudo apt install libbenchmark-dev libbenchmark-tools)
endif
endif

# Default target
all: $(TARGET)

# Link app
$(TARGET): $(APP_OBJS)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(APP_OBJS) -o $(TARGET) -pthread

# Compile src/*.cpp
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.cpp
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(DEPFLAGS) -c $< -o $@

# Compile tests/*.cpp
$(BUILD_DIR)/%.test.o: $(TEST_DIR)/%.cpp
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(DEPFLAGS) -c $< -o $@

# Compile bench/*.cpp. BENCH_CXXFLAGS is recorded in every results file.
$(BUILD_DIR)/%.bench.o: $(BENCH_DIR)/%.cpp
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(DEPFLAGS) $(BENCH_CPPFLAGS) -DBENCH_CXXFLAGS='"$(CXXFLAGS)"' -c $< -o $@

# Link tests
$(TEST_TARGET): $(LIB_OBJS) $(TEST_OBJS)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(LIB_OBJS) $(TEST_OBJS) $(TEST_FLAGS) -o $(TEST_TARGET)

# Link benchmarks
$(BENCH_TARGET): $(LIB_OBJS) $(BENCH_OBJS)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(LIB_OBJS) $(BENCH_OBJS) $(BENCH_LDFLAGS) $(BENCH_LIBS) -o $(BENCH_TARGET)

# Run tests
test: $(TEST_TARGET)
	./$(TEST_TARGET)

# Build benchmarks
bench: $(BENCH_TARGET)

# Full run, about 20 minutes: interleaved repetitions. The console shows mean, median, stddev
# and CV per benchmark; the JSON file keeps every repetition.
bench-run: $(BENCH_TARGET)
	@mkdir -p $(RESULTS_DIR)
	./$(BENCH_TARGET) $(BENCH_FLAGS) --benchmark_repetitions=$(BENCH_REPS) \
		--benchmark_enable_random_interleaving=true --benchmark_display_aggregates_only=true \
		--benchmark_out=$(RESULTS_DIR)/$(LABEL).json --benchmark_out_format=json $(ARGS)

# Quick check: one repetition, without the two largest sizes. Nothing is saved.
bench-quick: $(BENCH_TARGET)
	./$(BENCH_TARGET) $(BENCH_FLAGS) '--benchmark_filter=-n:(3000|4000)/' $(ARGS)

# Charts and summary.md from a results file, with the summary also copied into README.md
# between its results markers (needs: pip install matplotlib)
bench-plot:
	python3 $(BENCH_DIR)/plot.py $(RESULTS_DIR)/$(LABEL).json --out $(PLOTS_DIR) --readme README.md

# Statistical A/B comparison of two results files (needs: pip install scipy), e.g.
#   make bench-compare BASE=22af068 LABEL=simd-v1
bench-compare:
	python3 $(COMPARE_PY) benchmarks $(RESULTS_DIR)/$(BASE).json $(RESULTS_DIR)/$(LABEL).json

# Clean
clean:
	rm -rf $(BUILD_DIR)

# Run app
run: all
	./$(TARGET)

-include $(wildcard $(BUILD_DIR)/*.d)

.PHONY: all test bench bench-run bench-quick bench-plot bench-compare clean run
