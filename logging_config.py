import logging
from logging.handlers import RotatingFileHandler
import json

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
    json_handler = RotatingFileHandler(log_file, maxBytes=10000000, backupCount=5)
    json_handler.setFormatter(JsonFormatter())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonFormatter())

    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(json_handler)
    logger.addHandler(console_handler)

    return logger






# try:
#         result = 1 / 0
        
#     except ZeroDivisionError as e:
#         logger.error("Attempted to divide by zero. Values: a=%s, b=%s", 1, 2, exc_info=True)
#         raise