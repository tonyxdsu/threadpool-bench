#ifndef THREADPOOL_HPP
#define THREADPOOL_HPP

#include <functional>
#include <vector>
#include <thread>

class Threadpool {
public:
    /**
     * Constructs Threadpool object with a default number threads.
     */
    Threadpool();

    /**
     * Constructs Threadpool object with the defined number of threads.
     * 
     * @param numThreads The number of threads the threadpool will use.
     */
    Threadpool(unsigned int numThreads);

    /**
     * Will join all threads and delete the threadpool after all already scheduled tasks complete.
     */
    ~Threadpool();

    void enqueue(std::function<void()> task);

private:
    /**
     * All worker threads.
     */
    std::vector<std::thread> threads;

    /**
     * The number of worker threads.
     */
    unsigned int numThreads;

    /**
     * Worker thread loop.
     */
    void worker();
};

#endif