#ifndef THREADPOOL_HPP
#define THREADPOOL_HPP

#include <thread>
#include <condition_variable>
#include <functional>
#include <vector>
#include <queue>
#include <stdexcept>


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

    /**
     * Blocks until every task enqueued so far has finished running. Tasks enqueued concurrently
     * by other threads while waiting are also waited on. Must not be called from inside a task.
     */
    void waitAll();


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
     * Number of tasks that are queued or currently running.
     */
    unsigned int pendingTasks = 0;

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
     * Signalled when pendingTasks drops to zero.
     */
    std::condition_variable allDone;

    /**
     * True if the threadpool has joined. All tasks already enqueued will finish first before the threadpool is deleted.
     */
    bool stopFlag = false;
};

#endif