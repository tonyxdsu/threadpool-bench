#include "threadpool.hpp"

#include <iostream>

using std::vector;
using std::thread;

#define DEFAULT_NUM_THREADS 8

Threadpool::Threadpool() : Threadpool(DEFAULT_NUM_THREADS) {

}

Threadpool::Threadpool(unsigned int numThreads) {
    this->threads.reserve(numThreads);
    this->numThreads = numThreads;

    for (unsigned int i = 0; i < numThreads; i++) {
        threads.emplace_back(&Threadpool::worker, this);
    }
}

void Threadpool::enqueue(std::function<void()> task) {
    {
        std::unique_lock<std::mutex> lock(mutexLock);
        taskQueue.push(task);
    }
    hasTask.notify_one();
}

Threadpool::~Threadpool() {
    for (unsigned int i = 0; i < numThreads; i++) {
        threads[i].join();
    }
}

void Threadpool::worker() {
    while (true) {
        std::function<void()> task;
        {
            std::unique_lock<std::mutex> lock(mutexLock);
            while (taskQueue.empty()) {
                hasTask.wait(lock);
            }

            task = taskQueue.front();
            taskQueue.pop();
        }

        task();
    }
}