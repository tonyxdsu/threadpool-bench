#include "threadpool.hpp"

#include <gtest/gtest.h>
#include <atomic>
#include <chrono>
#include <future>
#include <mutex>
#include <vector>

TEST(ThreadpoolTest, DefaultConstruct) {
    Threadpool pool;
}

TEST(ThreadpoolTest, ConstructWithNumThreads) {
    Threadpool pool(8);
}

TEST(ThreadpoolTest, NoTasksEnqueued) {
    Threadpool pool(4);
}

TEST(ThreadpoolTest, AllTasksExecute) {
    std::atomic<int> counter{0};
    int numTasks = 4242;
    {
        Threadpool pool(4);
        for (int i = 0; i < numTasks; i++) {
            pool.enqueue([&counter] { counter++; });
        }
    }
    EXPECT_EQ(counter.load(), numTasks);
}

TEST(ThreadpoolTest, AllTasksExecuteSingleThread) {
    std::atomic<int> counter{0};
    int numTasks = 4242;
    {
        Threadpool pool(1);
        for (int i = 0; i < numTasks; i++) {
            pool.enqueue([&counter] { counter++; });
        }
    }
    EXPECT_EQ(counter.load(), numTasks);
}

TEST(ThreadpoolTest, AllTasksExecuteMoreTasksThanThreads) {
    std::atomic<int> counter{0};
    int numTasks = 6767;
    {
        Threadpool pool(8);
        for (int i = 0; i < numTasks; i++) {
            pool.enqueue([&counter] { counter++; });
        }
    }
    EXPECT_EQ(counter.load(), numTasks);
}

TEST(ThreadpoolTest, TasksRunConcurrently) {
    std::atomic<int> concurrent{0};
    std::atomic<int> maxConcurrent{0};
    int numThreads = 8;
    {
        Threadpool pool(numThreads);
        for (int i = 0; i < numThreads; i++) {
            pool.enqueue([&] {
                int cur = ++concurrent;
                int prev = maxConcurrent.load();
                while (cur > prev && !maxConcurrent.compare_exchange_weak(prev, cur)) {}
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                --concurrent;
            });
        }
    }
    EXPECT_GT(maxConcurrent.load(), 1);
}

TEST(ThreadpoolTest, TaskWithFuture) {
    std::promise<int> p;
    auto fut = p.get_future();
    {
        Threadpool pool(2);
        pool.enqueue([&p] { p.set_value(42); });
    }
    EXPECT_EQ(fut.get(), 42);
}

TEST(ThreadpoolTest, FIFOOrderSingleThread) {
    std::vector<int> order;
    std::mutex m;
    {
        Threadpool pool(1);
        for (int i = 0; i < 5; i++) {
            pool.enqueue([&order, &m, i] {
                std::lock_guard<std::mutex> lock(m);
                order.push_back(i);
            });
        }
    }
    EXPECT_EQ(order, (std::vector<int>{0, 1, 2, 3, 4}));
}