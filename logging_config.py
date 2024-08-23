import logging
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
import json
import queue

# Save a reference to the original makeRecord method
original_makeRecord = logging.Logger.makeRecord

# Define the custom makeRecord method
def make_record_with_extra(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
    # Create the original record using the original method
    record = original_makeRecord(self, name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)
    
    # Add custom _extra attribute to the record
    record._extra = extra
    return record

# Override the makeRecord method in the Logger class
logging.Logger.makeRecord = make_record_with_extra

class JsonFormatter(logging.Formatter):
    def format(self, record):
        extra = getattr(record, '_extra', {})
        
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'message': record.getMessage(),
            # 'name': record.name,
            # 'filename': record.pathname,
            'funcName': record.funcName,
            'lineno': record.lineno,
        }
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        if extra is not None :
            log_record.update(extra)
        return json.dumps(log_record)

def setup_logging(log_file='app.log.jsonl', level=logging.INFO):
    # Create a queue for the QueueHandler
    log_queue = queue.Queue()

    # Create handlers
    queue_handler = QueueHandler(log_queue)
    json_handler = RotatingFileHandler(log_file, maxBytes=10000000, backupCount=5)
    json_handler.setFormatter(JsonFormatter())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonFormatter())

    # Create a QueueListener to listen for records in the queue
    queue_listener = QueueListener(log_queue, json_handler, console_handler)
    queue_listener.start()

    # Setup the root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(queue_handler)

    return logger, queue_listener






# try:
#         result = 1 / 0
        
#     except ZeroDivisionError as e:
#         logger.error("Attempted to divide by zero. Values: a=%s, b=%s", 1, 2, exc_info=True)
#         raise