import logging
import time
import threading
from logging_config import JsonFormatter

# Function to generate log messages
def log_messages(logger, num_messages):
    for i in range(num_messages):
        logger.info(f"Log message number {i}", extra={"thread": threading.current_thread().name})
    print(f"Finished logging {num_messages} messages")

if __name__ == "__main__":
    import queue
    from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

    log_queue = queue.Queue()

    json_handler = RotatingFileHandler('app.log.jsonl', maxBytes=10000000, backupCount=5)
    json_handler.setFormatter(JsonFormatter())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonFormatter())

    queue_handler = QueueHandler(log_queue)
    queue_listener = QueueListener(log_queue, json_handler, console_handler)
    queue_listener.start()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(queue_handler)

    num_messages = 10000

    # Measure performance
    start_time = time.time()
    threads = [threading.Thread(target=log_messages, args=(logger, num_messages // 10)) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    end_time = time.time()

    print(f"Time taken for logging {num_messages} messages: {end_time - start_time} seconds")

    # Stop the QueueListener
    queue_listener.stop()
