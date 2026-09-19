#include "threadpool.hpp"

using std::vector;
using std::thread;

#include <iostream>

#define DEFAULT_NUM_THREADS 8
unsigned int defaultThreadCount() {
    unsigned int n = std::thread::hardware_concurrency();
    return n == 0 ? DEFAULT_NUM_THREADS : n;   // hardware_concurrency() may return 0 if it cannot tell
}

Threadpool::Threadpool() : Threadpool(defaultThreadCount()) {

}

Threadpool::Threadpool(unsigned int numThreads) {
    if (numThreads == 0) {
        throw std::invalid_argument("Threadpool: numThreads must be at least 1");
    }

    this->threads.reserve(numThreads);
    this->numThreads = numThreads;

    for (unsigned int i = 0; i < numThreads; i++) {
        threads.emplace_back(&Threadpool::worker, this);
    }
}

void Threadpool::enqueue(std::function<void()> task) {
    {
        std::unique_lock<std::mutex> lock(mutexLock);

        if (stopFlag) {
            throw std::runtime_error("Threadpool: enqueue called after destruction began");
        }

        taskQueue.push(std::move(task));
        pendingTasks++;
    }
    hasTask.notify_one();
}

void Threadpool::waitAll() {
    std::unique_lock<std::mutex> lock(mutexLock);
    while (pendingTasks != 0) {
        allDone.wait(lock);
    }
}

Threadpool::~Threadpool() {
    {
        std::unique_lock<std::mutex> lock(mutexLock);
        stopFlag = true;
    }
    hasTask.notify_all();

    for (unsigned int i = 0; i < numThreads; i++) {
        threads[i].join();
    }
}

void Threadpool::worker() {
    while (true) {
        std::function<void()> task;
        {
            std::unique_lock<std::mutex> lock(mutexLock);
            while (taskQueue.empty() && !stopFlag) {
                hasTask.wait(lock);
            }

            // at this point, either the queue is not empty, or the queue is empty and stopFlag = true

            if (stopFlag && taskQueue.empty()) {
                break;
            }

            task = taskQueue.front();
            taskQueue.pop();
        }

        task(); 
        
        {
            std::unique_lock<std::mutex> lock(mutexLock);
            pendingTasks--;
            if (pendingTasks == 0) {
                allDone.notify_all();
            }
        }
    }
}