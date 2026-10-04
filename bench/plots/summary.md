# Benchmark results: v0

- Machine: AMD Ryzen 7 9800X3D 8-Core Processor; 8 cores, 16 hardware threads; L1d 48 KiB and L2 1 MiB per core, L3 96 MiB shared by all 8 cores
- Build: gcc 13.3.0, `-std=c++17 -Wall -Wextra -Iinclude -pthread -O3 -march=native -g -falign-loops=64`, git v0
- Reference: OpenBLAS 0.3.26 NO_LAPACKE DYNAMIC_ARCH NO_AFFINITY Cooperlake MAX_THREADS=64 core=Cooperlake
- Run: 2026-10-04T00:47:28-07:00, median of 5 repetitions, wall-clock time, every result checked with Freivalds' algorithm

## Headline: n = 2000, tile 48

![GFLOP/s of each implementation at n = 2000](headline.png)

| Implementation | Threads | Time (ms) | GFLOP/s | vs naive | vs OpenBLAS, same threads | CV |
|---|---:|---:|---:|---:|---:|---:|
| multiplyNaive | 1 | 4,119 | 3.88 | 1x | 3.1% | 4.5% |
| multiplyBlocked | 1 | 2,273 | 7.04 | 1.81x | 5.7% | 1.2% |
| multiplyBlockedParallel | 8 | 339 | 47.2 | 12.1x | 9.2% | 1.6% |
| multiplyBlockedParallel | 16 | 267 | 59.9 | 15.4x | 7.1% | 1.0% |
| OpenBLAS dgemm | 1 | 130 | 123 | 31.8x | 100.0% | 1.4% |
| OpenBLAS dgemm | 8 | 31.2 | 512 | 132x | 100.0% | 3.2% |
| OpenBLAS dgemm | 16 | 19 | 840 | 216x | 100.0% | 2.7% |

## By matrix size, one thread

![GFLOP/s of naive and blocked by matrix size](throughput_vs_size.png)

![Cache misses per multiply-add by matrix size](cache_misses.png)

GFLOP/s, then hardware-counter events per multiply-add (N = naive, B = blocked).

| n | Naive | Blocked | Blocked / naive | OpenBLAS | L1D miss N | L1D miss B | L2 miss N | L2 miss B | DRAM fill N | DRAM fill B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 6.22 | 7.17 | 1.15x | 143 | 0.132 | 0.0212 | 5.22e-05 | 4.55e-05 | 4.77e-07 | 8.98e-07 |
| 200 | 5.66 | 7.15 | 1.26x | 108 | 0.13 | 0.0163 | 0.000504 | 0.00098 | 4.8e-06 | 2.77e-06 |
| 300 | 5.23 | 7.13 | 1.36x | 112 | 0.135 | 0.0148 | 0.000751 | 0.00105 | 1.38e-05 | 8.06e-06 |
| 500 | 4.85 | 7.22 | 1.49x | 115 | 0.162 | 0.0151 | 0.0284 | 0.00106 | 3.13e-05 | 1.73e-05 |
| 700 | 4.83 | 7.13 | 1.48x | 120 | 0.562 | 0.0137 | 0.0483 | 0.00151 | 7.51e-05 | 2.65e-05 |
| 1000 | 4.09 | 7.13 | 1.74x | 119 | 1.13 | 0.0136 | 0.0218 | 0.00232 | 7.12e-05 | 5.19e-05 |
| 1500 | 3.9 | 7.13 | 1.83x | 121 | 1.13 | 0.0135 | 0.0456 | 0.00286 | 2.58e-05 | 7.75e-05 |
| 2000 | 3.88 | 7.04 | 1.81x | 123 | 1.09 | 0.0141 | 0.0675 | 0.00319 | 6.06e-05 | 9.66e-05 |
| 3000 | 1.8 | 7.02 | 3.91x | 125 | 1.13 | 0.0141 | 0.0881 | 0.00326 | 0.013 | 0.000454 |
| 4000 | 1.12 | 7 | 6.25x | 125 | 1.16 | 0.0145 | 0.633 | 0.00347 | 0.0582 | 0.000986 |

## Thread scaling: n = 2000, tile 48

![Speedup by number of workers at n = 2000](thread_scaling.png)

Speedup is against single-threaded multiplyBlocked; efficiency divides it by the physical cores in use (at most 8). GHz is the average clock of the busy cores; IPC is per hardware thread.

| Workers | Time (ms) | GFLOP/s | Speedup | Efficiency | GHz | IPC | L1D miss/FMA | OpenBLAS GFLOP/s | OpenBLAS speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2,243 | 7.13 | 1.01 | 101% | 5.05 | 6.95 | 0.0142 | 123 | 1 |
| 2 | 1,190 | 13.4 | 1.91 | 96% | 5.04 | 6.6 | 0.0181 | 225 | 1.83 |
| 4 | 615 | 26 | 3.69 | 92% | 5.07 | 6.36 | 0.0205 | 404 | 3.27 |
| 6 | 425 | 37.6 | 5.34 | 89% | 5.09 | 6.12 | 0.0227 | 498 | 4.03 |
| 8 | 339 | 47.2 | 6.7 | 84% | 5.09 | 5.75 | 0.0267 | 512 | 4.15 |
| 10 | 302 | 53 | 7.53 | 94% | 5.08 | 5.2 | 0.0331 | 610 | 4.95 |
| 12 | 280 | 57.2 | 8.13 | 102% | 5.07 | 4.72 | 0.0409 | 691 | 5.6 |
| 14 | 270 | 59.2 | 8.41 | 105% | 5.04 | 4.18 | 0.0507 | 794 | 6.43 |
| 16 | 267 | 59.9 | 8.51 | 106% | 4.99 | 3.78 | 0.0608 | 840 | 6.81 |

## Tile sweep: n = 2000

![GFLOP/s by tile size at n = 2000](tile_sweep.png)

| Tile | 1 thread GFLOP/s | IPC | L1D miss/FMA | L2 miss/FMA | 8 workers GFLOP/s |
|---|---:|---:|---:|---:|---:|
| 8 | 6.67 | 7.79 | 0.0492 | 0.00784 | 27.7 |
| 16 | 7.04 | 7.38 | 0.0215 | 0.00509 | 38 |
| 24 | 7.04 | 7.18 | 0.0151 | 0.00427 | 43.4 |
| 32 | 7.01 | 6.96 | 0.0164 | 0.00531 | 46.7 |
| 48 | 7.04 | 6.95 | 0.0141 | 0.00319 | 47.2 |
| 64 | 6.52 | 6.28 | 0.0171 | 0.00249 | 42.4 |
| 96 | 6.24 | 5.99 | 0.139 | 0.00132 | 40.6 |
| 128 | 5.96 | 5.65 | 0.137 | 0.000856 | 39.3 |
| 192 | 5.32 | 5.07 | 0.136 | 0.000675 | 35.5 |
| 256 | 5.13 | 4.86 | 0.138 | 0.00155 | 33 |
| 384 | 4.81 | 4.56 | 0.788 | 0.0546 | 29.1 |
| 512 | 4.36 | 4.11 | 1.07 | 0.0931 | 26.8 |
