// Benchmarks for the matmul.hpp implementations. See bench/README.md for what each one
// answers and how to run them.
//
// Every benchmark times the public API call on fixed-seed n x n inputs that are built outside
// the timed loop. The timed region includes allocating the result, because callers pay for
// that too. Times are wall-clock: the pool's calling thread sleeps in waitAll(), so CPU time
// would hide the work done by its workers. Each result is checked after timing.

#include "bench_common.hpp"
#include "matmul.hpp"
#include "perf_counters.hpp"
#include "threadpool.hpp"

#include <benchmark/benchmark.h>

#include <chrono>
#include <fstream>
#include <string>
#include <thread>

#ifndef BENCH_CXXFLAGS
#define BENCH_CXXFLAGS "unknown"
#endif

namespace {

// Args: n.
void BM_Naive(benchmark::State& state) {
    const auto n = static_cast<std::size_t>(state.range(0));
    const Matrix A = randomMatrix(n, n, 1), B = randomMatrix(n, n, 2);
    Matrix C(0, 0);

    PerfCounters counters;
    counters.start();
    for (auto _ : state) {
        C = multiplyNaive(A, B);
        benchmark::DoNotOptimize(C);
    }
    counters.stop();
    bench::finish(state, A, B, C, &counters, true);
}

// Args: n, block size.
void BM_Blocked(benchmark::State& state) {
    const auto n = static_cast<std::size_t>(state.range(0));
    const auto blockSize = static_cast<std::size_t>(state.range(1));
    const Matrix A = randomMatrix(n, n, 1), B = randomMatrix(n, n, 2);
    Matrix C(0, 0);

    PerfCounters counters;
    counters.start();
    for (auto _ : state) {
        C = multiplyBlocked(A, B, blockSize);
        benchmark::DoNotOptimize(C);
    }
    counters.stop();
    bench::finish(state, A, B, C, &counters, true);
}

// Args: n, block size, workers.
void BM_BlockedParallel(benchmark::State& state) {
    const auto n = static_cast<std::size_t>(state.range(0));
    const auto blockSize = static_cast<std::size_t>(state.range(1));
    const auto workers = static_cast<unsigned int>(state.range(2));
    const Matrix A = randomMatrix(n, n, 1), B = randomMatrix(n, n, 2);
    Matrix C(0, 0);

    PerfCounters counters;      // before the pool, so its worker threads are counted too
    Threadpool pool(workers);   // thread start-up stays outside the timed loop
    counters.start();
    for (auto _ : state) {
        C = multiplyBlockedParallel(A, B, blockSize, pool);
        benchmark::DoNotOptimize(C);
    }
    counters.stop();
    bench::finish(state, A, B, C, &counters, workers == 1);
}

// Naive vs blocked: the size sweep.
void sizeArgs(benchmark::internal::Benchmark* b) {
    for (auto n : bench::kSizes) b->Args({n});
}

// The size sweep at the default tile, plus the tile sweep at kFixedN.
void blockedArgs(benchmark::internal::Benchmark* b) {
    for (auto n : bench::kSizes) b->Args({n, bench::kBlockSize});
    for (auto bs : bench::kTileSizes) {
        const bool alreadyAdded = bs == bench::kBlockSize && bench::contains(bench::kSizes, bench::kFixedN);
        if (!alreadyAdded) b->Args({bench::kFixedN, bs});
    }
}

// Thread scaling at the default tile, plus the tile sweep at kTileSweepWorkers workers.
void blockedParallelArgs(benchmark::internal::Benchmark* b) {
    const auto workers = bench::workerCounts();
    for (auto w : workers) b->Args({bench::kFixedN, bench::kBlockSize, w});
    for (auto bs : bench::kTileSizes) {
        const bool alreadyAdded = bs == bench::kBlockSize && bench::contains(workers, bench::kTileSweepWorkers);
        if (!alreadyAdded) b->Args({bench::kFixedN, bs, bench::kTileSweepWorkers});
    }
}

BENCHMARK(BM_Naive)
    ->Apply(sizeArgs)
    ->ArgNames({"n"})
    ->UseRealTime()
    ->MeasureProcessCPUTime()
    ->Unit(benchmark::kMillisecond);

BENCHMARK(BM_Blocked)
    ->Apply(blockedArgs)
    ->ArgNames({"n", "bs"})
    ->UseRealTime()
    ->MeasureProcessCPUTime()
    ->Unit(benchmark::kMillisecond);

BENCHMARK(BM_BlockedParallel)
    ->Apply(blockedParallelArgs)
    ->ArgNames({"n", "bs", "workers"})
    ->UseRealTime()
    ->MeasureProcessCPUTime()
    ->Unit(benchmark::kMillisecond);

// The CPU model from /proc/cpuinfo. Google Benchmark records only core count and caches.
std::string cpuModel() {
    std::ifstream cpuinfo("/proc/cpuinfo");
    std::string line;
    while (std::getline(cpuinfo, line)) {
        if (line.rfind("model name", 0) != 0) continue;
        const auto start = line.find_first_not_of(" \t", line.find(':') + 1);
        if (start != std::string::npos) return line.substr(start);
    }
    return "unknown";
}

}  // namespace

int main(int argc, char** argv) {
    benchmark::Initialize(&argc, argv);
    if (benchmark::ReportUnrecognizedArguments(argc, argv)) return 1;

#ifdef __clang__
    benchmark::AddCustomContext("compiler", "clang " __VERSION__);
#else
    benchmark::AddCustomContext("compiler", "gcc " __VERSION__);
#endif
    benchmark::AddCustomContext("cpu", cpuModel());
    benchmark::AddCustomContext("cxxflags", BENCH_CXXFLAGS);
    benchmark::AddCustomContext("block_size", std::to_string(bench::kBlockSize));
    benchmark::AddCustomContext("perf_counters", PerfCounters().describe());

    // OpenBLAS, if linked in, starts its worker threads when it loads, and they busy-wait for
    // about 60 ms. Let them go idle so they cannot slow down the first benchmark.
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    benchmark::RunSpecifiedBenchmarks();
    benchmark::Shutdown();
    return 0;
}
