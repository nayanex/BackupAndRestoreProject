import os
import time
import threading

from enum import Enum
from Queue import Queue
from threading import Lock

from logger import CustomLogger

MAX_THREAD = 5
SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

ThreadOutputIndex = Enum('ThreadOutputIndex', 'TH_NAME, TH_ELAPSED_TIME, TH_RESULT, TH_ERROR')


class SingleThread(threading.Thread):
    """
    Subclasses the default thread behaviour.

    Elapsed time is calculated at the end.

    Callback should return a tuple with (thread name, elapsed time, job output, exception message).
    """

    def __init__(self, thread_name, callback, function_name, *func_args):
        """
        Initialize custom Single Thread.

        :param thread_name: identification of the thread.
        :param callback: callback function to be called at the end of the thread.
        :param function_name: function to be executed by this thread.
        :param func_args: list of arguments to be passed to the previous informed function.
        """
        threading.Thread.__init__(self)

        self.thread_name = thread_name
        self.function = function_name
        self.args = func_args
        self.callback = callback

    def run(self):
        """Execute this thread."""
        start_time = time.time()

        result = None
        error_message = None

        try:
            result = self.function(*self.args)
        except Exception as e:
            error_message = e.message

        end_time = time.time()

        if self.callback is not None:
            self.callback(self.thread_name, end_time - start_time, result, error_message)


class ThreadPool:
    """
    Creates and control the throughput of threads.

    Callback should return a tuple with ([thread name, elapsed time, job output, error_message],
    variables defined while creating the thread pool).
    """

    def __init__(self, logger, max_threads=MAX_THREAD, callback=None, *callback_args):
        """
        Initialize custom Thread Pool.

        :param logger: log object.
        :param max_threads: maximum number of threads to be running at the moment.
        """
        self.threads_queue = Queue()
        self.max_threads = max_threads
        self.running_threads = []
        self.callback = callback
        self.callback_args = callback_args
        self.mutex = Lock()
        self.logger = CustomLogger(SCRIPT_FILE, logger.log_root_path, logger.log_file_name,
                                   logger.log_level)

    def on_finished(self, thread_name, elapsed_time=0.0, result=None, error_message=None):
        """
        Call this callback at the end of the thread to print information.

        :param thread_name:  name of the thread.
        :param elapsed_time: elapsed time after the thread completion.
        :param result: output of the thread.
        :param error_message: error message caused by an exception from the job.
        """
        self.logger.log_time("Finishing thread {} with elapsed time"
                             .format(thread_name), elapsed_time)

        if self.callback is not None:
            self.mutex.acquire()
            self.callback([thread_name, elapsed_time, result, error_message], *self.callback_args)
            self.mutex.release()

    def create_thread(self, thread_name, function_name, *func_args):
        """
        Create a new thread with the specified arguments.

        :param thread_name:   name of the thread.
        :param function_name: function to be executed by the thread.
        :param func_args:     arguments of the function
        """
        self.logger.info("Creating thread {}.".format(thread_name))

        self.threads_queue.put(SingleThread(thread_name, self.on_finished,
                                            function_name, *func_args))

    def get_pool_size(self):
        """
        Get number of created threads in this pool.

        :return: number of threads.
        """
        return self.threads_queue.qsize()

    def pop_start_thread(self):
        """
        Pops the thread from the queue and starts it.

        :return: new running thread reference.
        """
        if not self.threads_queue.empty():
            th = self.threads_queue.get()
            th.start()
            return th
        return None

    def clean_running_thread_list(self):
        """Clean list in the running threads to allow others to start."""
        currently_running = []
        for running_th in self.running_threads:
            if running_th.isAlive():
                currently_running.append(running_th)
            else:
                del running_th

        del self.running_threads[:]
        self.running_threads = currently_running

    def start_pool(self):
        """Start the pool of created threads."""
        while not self.threads_queue.empty():
            if len(self.running_threads) < self.max_threads:
                self.running_threads.append(self.pop_start_thread())

            self.clean_running_thread_list()

        for running_th in self.running_threads:
            if running_th.isAlive():
                running_th.join()
        del self.running_threads[:]

# Sample of usage:
# def test(n, t):
#     print "Thread {} is doing stuff...".format(n)
#     time.sleep(t/2)
#
#
# tp = ThreadPool(get_logger(SCRIPT_FILE), 1)
#
# for i in range(0, 10):
#     name = "Thread-{}".format(i)
#     tp.create_thread(name, test, name, i)
#
# start_time = time.time()
# tp.start_pool()
# end_time = time.time()
# print("Finished in {0:.2f}s".format(end_time - start_time))
