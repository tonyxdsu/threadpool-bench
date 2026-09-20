#include "matmul.hpp"

#include <random>

Matrix multiplyNaive(const Matrix& A, const Matrix& B) {
    // TODO: classic i-j-k triple loop over A.rows x B.cols, accumulating over A.cols.
    Matrix C(A.rows, B.cols);
    return C;
}

Matrix multiplyBlocked(const Matrix& A, const Matrix& B, std::size_t blockSize) {
    // TODO: walk output tiles (ii, jj) and k-blocks (kk), then run the inner triple loop
    // over each tile. Remember the tail tiles when a dimension is not a multiple of blockSize.
    Matrix C(A.rows, B.cols);
    return C;
}

Matrix multiplyBlockedParallel(const Matrix& A, const Matrix& B, std::size_t blockSize, Threadpool& pool) {
    // TODO: partition C into disjoint tiles, enqueue one multiplyBlock call per tile, then
    // block here until every tile has finished before returning C.
    Matrix C(A.rows, B.cols);
    return C;
}

void multiplyBlock(const Matrix& A, const Matrix& B, Matrix& C,
                   std::size_t rowStart, std::size_t rowEnd,
                   std::size_t colStart, std::size_t colEnd,
                   std::size_t blockSize) {
    // TODO: accumulate C[rowStart..rowEnd) x [colStart..colEnd) over all of A.cols,
    // blocking the K loop by blockSize.
}

Matrix randomMatrix(std::size_t rows, std::size_t cols, unsigned int seed) {
    // TODO: fill with std::mt19937 + std::uniform_real_distribution seeded by seed.

    std::mt19937 gen(seed);
    std::uniform_real_distribution<> dis(-1000.0, 1000.0);

    Matrix m(rows, cols);

    for (int i = 0; i < rows * cols; i++) {
        m.data[i] = dis(gen);
    }

    return m;
}

bool matricesEqual(const Matrix& a, const Matrix& b, double tolerance) {
    if (a.data.size() != b.data.size()) {
        return false;
    }

    for (int i = 0; i < a.data.size(); i++) {
        if (std::fabs(a.data[i] - b.data[i]) > tolerance) {
            return false;
        }
    }

    return true;
}
