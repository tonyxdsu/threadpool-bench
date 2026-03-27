#include "threadpool.hpp"

#include <iostream>

using std::vector;
using std::thread;

#define DEFAULT_NUM_THREADS 8

Threadpool::Threadpool() : Threadpool(DEFAULT_NUM_THREADS) {

}

Threadpool::Threadpool(unsigned int numThreads) {
    this->numThreads = numThreads;

    for (unsigned int i = 0; i < numThreads; i++) {
        threads.emplace_back(&Threadpool::worker, this);
    }
}

Threadpool::~Threadpool() {
    for (unsigned int i = 0; i < numThreads; i++) {
        threads[i].join();
    }
}

void Threadpool::worker() {
    while (true) {
        std::cout << "Hello world!" << std::endl;
        break;
    }
}