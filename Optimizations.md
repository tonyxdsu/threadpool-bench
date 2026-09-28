# Optimizations to revisit

Notes on what is still slow in `multiplyBlock` after cache blocking. Cache blocking
makes sure the data is *nearby*. These are about how fast the core can *compute* on
it once it is. They are hints, not solutions.

Current inner structure, per output tile:

```
for each K-block
    for i in tile rows
        for j in tile cols
            sum = 0
            for k in K-block
                sum += A[i][k] * B[k][j]
            C[i][j] += sum
```

---

## 1. The dependency chain (FMA latency)

`sum += A[i][k] * B[k][j]` compiles to one fused multiply-add (FMA) per `k`. Each
FMA needs the `sum` produced by the previous one, so they cannot overlap.

- An FMA on Zen 5 has a **latency** of about 4 cycles: the time until its result is
  usable.
- The core has 2 FMA units, each able to **start** a new FMA every cycle
  (**throughput**).
- A single dependent chain therefore runs at about 1 FMA per 4 cycles, while the
  hardware could start about 8 in that time. Roughly 7/8 of the FMA capacity sits idle.

The loop is **latency-bound**, not memory-bound. Better caching cannot fix it.

**Guiding questions**
- If the innermost loop had *no* value carried from one iteration to the next,
  what would stop consecutive FMAs from overlapping?
- In the `i`, `k`, `j` loop order, what does the innermost loop write to? Does
  iteration `j + 1` need anything that iteration `j` produced?
- (The other classic fix: several independent partial sums interleaved in one loop.
  Worth knowing, but the loop order change gets it for free here.)

---

## 2. SIMD (vectorization)

With `-march=native`, the compiler may use AVX-512 instructions, which do one FMA on
**8 doubles at once**. Right now it cannot, for two reasons:

1. **Floating-point reductions are not reordered.** Vectorizing `sum += ...` over `k`
   means adding in a different order. FP addition is not associative, so the compiler
   will not do it unless you allow it (`-ffast-math` / `-fassociative-math`).
2. **Strided access.** Over `k`, `B[k][j]` walks *down a column*, so consecutive
   values are `B.cols * 8` bytes apart. SIMD loads want values next to each other
   in memory.

Combined with the latency chain above, the scalar i-j-k loop uses roughly 1/64 of what
one core can do: 8 lanes × 2 units × about 4× from latency.

**Guiding questions**
- Which loop order makes the innermost loop walk along a **row** of B *and* a row
  of C, both contiguous?
- In that order, is the innermost loop still a reduction into a single value, or
  is each iteration independent? Does the compiler then need `-ffast-math`?
- What value in that innermost loop stays the same across all its iterations, and
  where should it live?

**Related: the tail `break` (TODO in `multiplyBlock`)**
A loop with an early `break` has no trip count known in advance, so the compiler
usually will not vectorize or unroll it. The branch predictor is not the problem.
Hint: `multiplyBlocked` already handles tails without a per-iteration check
(`rowEnd = std::min(...)`). The K dimension can be handled the same way.

---

## How to check what the compiler did

- **Vectorization report:** add `-fopt-info-vec-optimized` (what got vectorized) or
  `-fopt-info-vec-missed` (what did not, and why) to `OPTFLAGS` and rebuild
  `src/matmul.cpp`. Look for the line numbers of your inner loop.
- **Look at the instructions:** `objdump -d -C --no-show-raw-insn build/matmul.o` and
  find `multiplyBlock`.
  - `vfmadd...pd` with `zmm` registers means 8-wide AVX-512.
  - `ymm` means 4-wide AVX2.
  - `vfmadd...sd` means scalar: one double at a time.
- **Measure:** time naive vs blocked vs reordered at n = 2048 and report GFLOP/s
  (`2·n³ / seconds / 1e9`). Change one thing at a time.
