#include "threadpool.hpp"

#include <gtest/gtest.h>

// TEST(ThreadpoolTest, Construct) {
//     Threadpool pool;
// }

// TEST(ThreadpoolTest, ConstructWithNumThreads) {
//     Threadpool pool(8);
// }

void taskHelloWorld() {
    std::cout << "Hello world!" << std::endl;
}

TEST(ThreadpoolTest, EnqueueEightTasks) {
    Threadpool pool(8);
    for (int i = 0; i < 8; i++) {
        pool.enqueue(taskHelloWorld);
    }
}

TEST(ThreadpoolTest, EnqueueMoreTasksThanThreads) {
    Threadpool pool(8);
    for (int i = 0; i < 37; i++) {
        pool.enqueue(taskHelloWorld);
    }
}