# -*- encoding: utf-8 -*-

import logging
import logging.handlers

LOG_BASIC_FORMAT = "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)s] %(message)s"

def init_logger(log_file=None):
    if len(logging.root.handlers) == 0:
        if log_file:
            handler = logging.handlers.RotatingFileHandler(log_file,
                                                           maxBytes=10 * 1024 * 1024,
                                                           backupCount=7)
            formatter = logging.Formatter(LOG_BASIC_FORMAT)
            handler.setFormatter(formatter)
            logging.root.addHandler(handler)
            
        logging.BASIC_FORMAT = LOG_BASIC_FORMAT
        logging.root.setLevel(logging.DEBUG)
        logging.info("Init logger success.")
    return logging.root
