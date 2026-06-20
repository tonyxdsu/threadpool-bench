#ifndef THREADPOOL_HPP
#define THREADPOOL_HPP

#include <thread>
#include <condition_variable>
#include <functional>
#include <vector>
#include <queue>


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

    /**
     * Queues a task for execution. All tasks already on the queue prior to threadpool destruction will be executed.
     * Any tasks added after destruction results in undefined behavior.
     * 
     * @param task The task to be executed by the threadpool. The task should not throw any exceptions.
     */
    void enqueue(std::function<void()> task);

private:
    /**
     * All worker threads.
     */
    std::vector<std::thread> threads;

    /**
     * Task queue.
     */
    std::queue<std::function<void()>> taskQueue;

    /**
     * The number of worker threads.
     */
    unsigned int numThreads;

    /**
     * Worker thread loop.
     */
    void worker();

    /**
     * Mutex.
     */
    std::mutex mutexLock;

    /**
     * Condition variable used to signal a new item in the task queue.
     */
    std::condition_variable hasTask;

    /**
     * True if the threadpool has joined. All tasks already enqueued will finish first before the threadpool is deleted.
     */
    bool stopFlag = false;
};

#endif