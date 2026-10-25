// Loop-carried dependency chains: what one costs, and two ways to remove it.
//
// Part 1 computes the column sums of an R x C row-major matrix two ways:
//   A, down:   for each column, walk down it, summing into one variable. Every add needs the
//              result of the add before it, so the adds form one chain.
//   B, across: for each row, add it into every column's total. Consecutive adds go to different
//              totals, so none of them waits for the one before.
// Both do the same adds in the same order for each column, so their results are bit-identical.
//
// Part 2 sums one array into 1, 2, 4 or 8 separate totals: the multiple-accumulator fix.
//
// Every kernel is timed in core cycles and retired instructions with PerfCounters. Run it with
// `make chain-demo`, which builds this file with and without auto-vectorization. Results and
// what they show are in experiments/Experiments.md.

#include "perf_counters.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdio>
#include <random>
#include <vector>

#ifndef EXP_CXXFLAGS
#define EXP_CXXFLAGS "unknown"
#endif

namespace {

// The kernels are noinline so each one is a separate function in objdump, and so the compiler
// cannot merge it into the timing loop around it.

// A: walk down each column, keeping its running total in one variable.
__attribute__((noinline)) void colSumsDown(const double* M, std::size_t R, std::size_t C,
                                           double* colSum) {
    for (std::size_t j = 0; j < C; j++) {
        double s = 0;
        for (std::size_t i = 0; i < R; i++) {
            s += M[i * C + j];
        }
        colSum[j] = s;
    }
}

// B: walk across each row, adding it into every column's total.
__attribute__((noinline)) void colSumsAcross(const double* M, std::size_t R, std::size_t C,
                                             double* colSum) {
    for (std::size_t j = 0; j < C; j++) colSum[j] = 0;
    for (std::size_t i = 0; i < R; i++) {
        for (std::size_t j = 0; j < C; j++) {
            colSum[j] += M[i * C + j];
        }
    }
}

// Sum of a[0, n) into 1, 2, 4 or 8 separate totals, combined at the end. n must be a multiple
// of 8.
__attribute__((noinline)) double sum1(const double* a, std::size_t n) {
    double s = 0;
    for (std::size_t i = 0; i < n; i++) s += a[i];
    return s;
}

__attribute__((noinline)) double sum2(const double* a, std::size_t n) {
    double s0 = 0, s1 = 0;
    for (std::size_t i = 0; i < n; i += 2) {
        s0 += a[i];
        s1 += a[i + 1];
    }
    return s0 + s1;
}

__attribute__((noinline)) double sum4(const double* a, std::size_t n) {
    double s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    for (std::size_t i = 0; i < n; i += 4) {
        s0 += a[i];
        s1 += a[i + 1];
        s2 += a[i + 2];
        s3 += a[i + 3];
    }
    return (s0 + s1) + (s2 + s3);
}

__attribute__((noinline)) double sum8(const double* a, std::size_t n) {
    double s0 = 0, s1 = 0, s2 = 0, s3 = 0, s4 = 0, s5 = 0, s6 = 0, s7 = 0;
    for (std::size_t i = 0; i < n; i += 8) {
        s0 += a[i];
        s1 += a[i + 1];
        s2 += a[i + 2];
        s3 += a[i + 3];
        s4 += a[i + 4];
        s5 += a[i + 5];
        s6 += a[i + 6];
        s7 += a[i + 7];
    }
    return ((s0 + s1) + (s2 + s3)) + ((s4 + s5) + (s6 + s7));
}

// Keeps the compiler from discarding sums whose results are otherwise unused.
volatile double sink;

// Cost per add of one kernel.
struct Cost {
    double cycles;
    double instructions;
};

// Runs `run`, which does addsPerRun adds, once to warm up, then for 7 trials of about 4e8 adds
// each. Returns the trial with the fewest cycles, the one least disturbed by interrupts and
// other programs.
template <class F>
Cost measure(PerfCounters& counters, F run, double addsPerRun) {
    const long reps = std::max(1L, static_cast<long>(4e8 / addsPerRun));
    run();
    Cost best{1e300, 0};
    for (int trial = 0; trial < 7; trial++) {
        counters.start();
        for (long r = 0; r < reps; r++) run();
        counters.stop();
        const double adds = addsPerRun * reps;
        const double cycles = counters.value(PerfCounters::Cycles) / adds;
        if (cycles < best.cycles) {
            best = {cycles, counters.value(PerfCounters::Instructions) / adds};
        }
    }
    return best;
}

}  // namespace

int main() {
    PerfCounters counters;
    if (!counters.isOpen(PerfCounters::Cycles) || !counters.isOpen(PerfCounters::Instructions)) {
        std::printf("Needs the cycle and instruction counters. %s\n", counters.describe().c_str());
        return 1;
    }
    std::printf("Built with: %s\n\n", EXP_CXXFLAGS);

    std::mt19937 gen(42);
    std::uniform_real_distribution<> dis(-1.0, 1.0);

    std::printf("Column sums: cycles and instructions per add\n");
    std::printf("%6s x %-6s %6s %9s %10s %7s %8s %8s\n", "R", "C", "KiB", "A: down", "B: across",
                "A / B", "A instr", "B instr");
    // Six 32 KiB matrices, from tall to square, so A's chains shrink from 2048 adds to 64.
    // Then the benchmarks' 48 x 48 tile, and one matrix far bigger than L2.
    const std::size_t shapes[][2] = {{2048, 2}, {1024, 4}, {512, 8},  {256, 16},
                                     {128, 32}, {64, 64},  {48, 48}, {2000, 2000}};
    for (const auto& shape : shapes) {
        const std::size_t R = shape[0], C = shape[1];
        std::vector<double> M(R * C), down(C), across(C);
        for (double& x : M) x = dis(gen);
        const double adds = static_cast<double>(R * C);
        const Cost a = measure(counters, [&] { colSumsDown(M.data(), R, C, down.data()); }, adds);
        const Cost b = measure(counters, [&] { colSumsAcross(M.data(), R, C, across.data()); }, adds);
        std::printf("%6zu x %-6zu %6.0f %9.2f %10.2f %6.1fx %8.2f %8.2f  %s\n", R, C,
                    adds * sizeof(double) / 1024, a.cycles, b.cycles, a.cycles / b.cycles,
                    a.instructions, b.instructions, down == across ? "identical" : "DIFFERENT");
    }

    std::printf("\nSum of 4096 doubles (32 KiB): cycles and instructions per add\n");
    std::printf("%8s %8s %8s\n", "", "cycles", "instr");
    std::vector<double> v(4096);
    for (double& x : v) x = dis(gen);
    double (*const sums[])(const double*, std::size_t) = {sum1, sum2, sum4, sum8};
    const int totals[] = {1, 2, 4, 8};
    for (int s = 0; s < 4; s++) {
        const Cost c = measure(counters, [&] { sink = sums[s](v.data(), v.size()); },
                               static_cast<double>(v.size()));
        std::printf("%d total%s %8.2f %8.2f\n", totals[s], totals[s] == 1 ? " " : "s", c.cycles,
                    c.instructions);
    }
}
