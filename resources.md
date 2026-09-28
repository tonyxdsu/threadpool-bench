# Learning resources: performance, SIMD, vectorization

Picked for where this project is: C++ matrix multiply, cache blocking done, threads next.
See [Optimizations.md](Optimizations.md) for the open hints these resources help with.

## Courses

### MIT 6.172: Performance Engineering of Software Systems (top pick)
- Free on MIT OpenCourseWare. The Fall 2018 run has full lecture videos.
  Taught by Charles Leiserson and Julian Shun.
- **Lecture 1 is a case study of this exact problem.** It takes matrix multiply
  from Python to heavily optimized C in steps (loop order, compiler flags,
  parallelism, tiling, vectorization) and measures the speedup at each step.
- Later lectures cover bit tricks, compiler behavior, multicore, races and
  synchronization, which is relevant to the threadpool too.

### UT Austin: LAFF-On Programming for High Performance (matmul in depth)
- By Robert van de Geijn and Margaret Myers (the BLIS group).
  Free at ulaff.net; it has also run on edX.
- The whole course is one matrix multiply, optimized step by step:
  - loop orderings
  - register blocking (keeping a small block of C in registers)
  - AVX2 intrinsics and FMA
  - cache blocking at several levels
  - OpenMP parallelism
- It picks up where Optimizations.md leaves off and goes to near-BLAS
  performance. Written in C, but everything carries over to C++.

## Book

### Computer Systems: A Programmer's Perspective, by Bryant and O'Hallaron
The CMU textbook for 15-213.
- **Chapter 5, "Optimizing Program Performance":** the clearest explanation of
  latency-bound vs throughput-bound loops, several independent accumulators and
  loop unrolling. This is the dependency-chain issue in Optimizations.md, section 1.
- **Chapter 6, the memory hierarchy:** includes blocked matrix multiply and
  loop-order analysis.
- It covers vectorization only briefly, but it builds the model of how a CPU runs
  code that everything else relies on.

## Free references

- **Algorithms for Modern Hardware, by Sergey Slotin** (en.algorithmica.org/hpc).
  A free online book, not a university course, but excellent. It has strong
  chapters on SIMD and a matrix multiply case study.
- **Agner Fog's optimization manuals and instruction tables** (agner.org/optimize).
  The source for per-instruction latency and throughput numbers, like the
  "4 cycles" for FMA.
- **Intel Intrinsics Guide.** A searchable reference for when you start writing
  intrinsics like `_mm512_fmadd_pd` by hand.

## Suggested path

1. **Now:** watch MIT 6.172 lecture 1 (about an hour). It puts blocking, loop
   order, vectorization and parallelism in context.
2. **When doing the loop reorder:** read CS:APP chapter 5.
3. **If you want to go further:** work through LAFF-On for BLAS-level
   performance.
