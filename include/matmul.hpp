#ifndef MATMUL_HPP
#define MATMUL_HPP

#include "threadpool.hpp"

#include <cstddef>
#include <vector>

/**
 * Dense, row-major matrix. Element (r, c) lives at data[r * cols + c].
 */
struct Matrix {
    /**
     * Element storage, row-major. Size is rows * cols.
     */
    std::vector<double> data;

    /**
     * Number of rows.
     */
    std::size_t rows;

    /**
     * Number of columns.
     */
    std::size_t cols;

    /**
     * Constructs a zero-initialized rows x cols matrix.
     */
    Matrix(std::size_t rows, std::size_t cols)
        : data(rows * cols, 0.0), rows(rows), cols(cols) {}

    /**
     * Accesses element (r, c). No bounds checking.
     */
    double& at(std::size_t r, std::size_t c) { return data[r * cols + c]; }

    /**
     * Accesses element (r, c). No bounds checking.
     */
    const double& at(std::size_t r, std::size_t c) const { return data[r * cols + c]; }
};

/**
 * Naive single-threaded triple-loop multiply. This is the correctness reference
 * and the baseline every other variant is measured against.
 *
 * @param A Left operand, M x K.
 * @param B Right operand, K x N.
 * @return The M x N product.
 */
Matrix multiplyNaive(const Matrix& A, const Matrix& B);

/**
 * Cache-blocked single-threaded multiply. Compare against multiplyNaive to see the
 * cache-locality win in isolation, before any threading is involved.
 *
 * @param A Left operand, M x K.
 * @param B Right operand, K x N.
 * @param blockSize Tile edge length. Tune so three blockSize x blockSize tiles fit in L1/L2.
 * @return The M x N product.
 */
Matrix multiplyBlocked(const Matrix& A, const Matrix& B, std::size_t blockSize);

/**
 * Cache-blocked multiply parallelized across a Threadpool. Each enqueued task should own
 * a disjoint output tile of C, so no two tasks ever write the same element and no locking
 * is needed around C.
 *
 * @param A Left operand, M x K.
 * @param B Right operand, K x N.
 * @param blockSize Tile edge length, also determines how many tasks are produced.
 * @param pool The threadpool to distribute tile computations across.
 * @return The M x N product.
 */
Matrix multiplyBlockedParallel(const Matrix& A, const Matrix& B, std::size_t blockSize, Threadpool& pool);

/**
 * Computes one output tile of C: rows [rowStart, rowEnd) by columns [colStart, colEnd).
 * Accumulates over the full K dimension internally, so the tile is complete when this
 * returns and the call is self-contained enough to hand straight to Threadpool::enqueue.
 *
 * @param A Left operand, M x K.
 * @param B Right operand, K x N.
 * @param C Output matrix, M x N. Only the named tile is written.
 * @param rowStart First row of the tile, inclusive.
 * @param rowEnd One past the last row of the tile.
 * @param colStart First column of the tile, inclusive.
 * @param colEnd One past the last column of the tile.
 * @param blockSize Tile edge length used for blocking the K loop.
 */
void multiplyBlock(const Matrix& A, const Matrix& B, Matrix& C,
                   std::size_t rowStart, std::size_t rowEnd,
                   std::size_t colStart, std::size_t colEnd,
                   std::size_t blockSize);

/**
 * Builds a matrix filled with pseudorandom values for benchmarking.
 *
 * @param rows Number of rows.
 * @param cols Number of columns.
 * @param seed Seed for the generator, so runs are reproducible.
 * @return The filled matrix.
 */
Matrix randomMatrix(std::size_t rows, std::size_t cols, unsigned int seed);

/**
 * Compares two matrices elementwise within a tolerance. Floating-point multiply reorders
 * differently between the naive and blocked variants, so exact equality will not hold.
 *
 * @param a First matrix.
 * @param b Second matrix.
 * @param tolerance Maximum permitted absolute difference per element.
 * @return True if dimensions match and every element is within tolerance.
 */
bool matricesEqual(const Matrix& a, const Matrix& b, double tolerance);

#endif
