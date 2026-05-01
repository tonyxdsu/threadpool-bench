#include "threadpool.hpp"

#include <gtest/gtest.h>

TEST(ThreadpoolTest, Construct) {
    Threadpool pool(8);
}