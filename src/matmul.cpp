#include "matmul.hpp"

#include <random>

Matrix multiplyNaive(const Matrix& A, const Matrix& B) {
    if (A.cols != B.rows) {
        throw std::invalid_argument("Matrix dimensions do not match for multiplication");
    }

    Matrix C(A.rows, B.cols);

    // We'll say A is i rows by k columns,
    //           B is k rows by j columns
    // and       C is i rows by j columns

    for (size_t i = 0; i < A.rows; i++) {
        for (size_t j = 0; j < B.cols; j++) {
            double sum = 0;
            for (size_t k = 0; k < A.cols; k++) {
                sum += A.at(i, k) * B.at(k, j);
            }
            C.at(i, j) = sum;
        }
    }

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
    std::mt19937 gen(seed);
    std::uniform_real_distribution<> dis(-1000.0, 1000.0);

    Matrix m(rows, cols);

    for (size_t i = 0; i < rows * cols; i++) {
        m.data[i] = dis(gen);
    }

    return m;
}

bool matricesEqual(const Matrix& a, const Matrix& b, double tolerance) {
    if (a.rows != b.rows || a.cols != b.cols) {
        return false;
    }

    for (size_t i = 0; i < a.data.size(); i++) {
        if (std::fabs(a.data[i] - b.data[i]) > tolerance) {
            return false;
        }
    }

    return true;
}
