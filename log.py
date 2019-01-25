import time
import logging
import threading

class Log(object):

    _loggers = {}

    CRITICAL=logging.CRITICAL
    ERROR=logging.ERROR
    WARNING=logging.WARNING
    INFO=logging.INFO
    DEBUG=logging.DEBUG
    NOTSET=logging.NOTSET

    chosen_level=logging.INFO

    COLOURS = {
        "critical": "\033[1;31;40m", # red
        "error": "\033[1;33;40m", # yellow
        "warning": "\033[1;35;40m", # purple
        "info": "\033[1;37;40m", # white
        "debug": "\033[1;37;40m" # grey
    }

    @staticmethod
    def debug(tag, message=None):
        """
        Post a debug-level message.
        
        :param String tag: tag for the log message.
        :param String message: message to post, if one is not provided, the tag
                                is used as the message instead.
        :return: None
        """
        Log._post("debug", tag, message)

    @staticmethod
    def info(tag, message=None):
        """
        Post an info-level message.
        
        :param String tag: tag for the log message.
        :param String message: message to post, if one is not provided, the tag
                                is used as the message instead.
        :return: None
        """
        Log._post("info", tag, message)

    @staticmethod
    def warning(tag, message=None):
        """
        Post a warning-level message.
        
        :param String tag: tag for the log message.
        :param String message: message to post, if one is not provided, the tag
                                is used as the message instead.
        :return: None
        """
        Log._post("warning", tag, message)

    @staticmethod
    def error(tag, message=None):
        """
        Post an error-level message.
        
        :param String tag: tag for the log message.
        :param String message: message to post, if one is not provided, the tag
                                is used as the message instead.
        :return: None
        """
        Log._post("error", tag, message)

    @staticmethod
    def critical(tag, message=None):
        """
        Post a critical-level message.
        
        :param String tag: tag for the log message.
        :param String message: message to post, if one is not provided, the tag
                                is used as the message instead.
        :return: None
        """
        Log._post("critical", tag, message)

    @staticmethod
    def log(tag, message=None):
        """
        Post a log-level message.
        
        :param String tag: tag for the log message.
        :param String message: message to post, if one is not provided, the tag
                                is used as the message instead.
        :return: None
        """
        Log._post("log", tag, message)

    @staticmethod
    def exception(tag, message=None):
        """
        Post an exception-level message.
        
        :param String tag: tag for the log message.
        :param String message: message to post, if one is not provided, the tag
                                is used as the message instead.
        :return: None
        """
        Log._post("exception", tag, message)

    @staticmethod
    def init(level):
        """
        Initiate the logging system.
        
        :param int level: level to set for the logger (only applies on first 
                                call, can't be changed once logger is created).
        :return: Logger
        """
        Log.chosen_level = level
        logging.basicConfig(
            format="%(levelname)s\t%(name)s\t%(asctime)s\t%(message)s",
            level=level)

    @staticmethod
    def _post(level, tag, message=None):
        """
        Post a message to a logger of a given tag at the given level.
        
        :param String tag: tag for the log message.
        :param String level: level of the log message, as a lowercase String,
        :param String message: message to post, the message is posted as-is, but
                        in the right colour.
        :return: None
        """
        if message == None:
            message = tag
            tag = "hotword"

        message = "%s%s\033[0;37;40m" % (Log.COLOURS[level], message)

        logger = Log._get_logger(level, tag)
        method = getattr(logger, level)
        method(Log._message(message))

    @staticmethod
    def _get_logger(level, tag):
        """
        Retrieve a Logger for a given tag.
        
        :param int level: level to set for the logger (only applies on first 
                                call, can't be changed once logger is created).
        :param String tag: tag for the log message.
        :return: Logger
        """
        try:
            return Log._loggers[tag]
        except KeyError:
            Log._loggers[tag] = logging.getLogger(tag)
            Log._loggers[tag].setLevel(Log.chosen_level)
            return Log._loggers[tag]

    @staticmethod
    def _message(message):
        """
        Augment a message by including Thread information.

        :param String message: message to post, adds time and Thread information
                                to the String.
        :return: String
        """
        str_thread = "Thread-%d" % threading.current_thread().ident
        return "%s\t%s" % (str_thread, message)
