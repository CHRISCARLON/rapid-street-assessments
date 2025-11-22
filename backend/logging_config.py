import logging
import json

from datetime import datetime
from logging.config import dictConfig
from pathlib import Path
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_record = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        usrn = getattr(record, "usrn", None)
        if usrn is not None:
            log_record["usrn"] = usrn

        duration = getattr(record, "duration", None)
        if duration is not None:
            log_record["duration"] = duration

        status_code = getattr(record, "status_code", None)
        if status_code is not None:
            log_record["status_code"] = status_code

        return json.dumps(log_record)


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 10485760,  # 10 MB
    backup_count: int = 5,
    enable_file_logging: bool = True,
) -> None:
    """
    Configure the logging system for the app

    Args:
        log_level: The minimum log level to record (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        max_bytes: Maximum size of each log file before rotation (default: 10 MB)
        backup_count: Number of backup log files to keep (default: 5)
        enable_file_logging: Enable file-based logging (set to False in Docker for stdout only)
    """

    if enable_file_logging:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

    handlers_list = ["console"]
    if enable_file_logging:
        handlers_list.extend(["file_json", "error_file"])

    error_handlers_list = ["console"]
    if enable_file_logging:
        error_handlers_list.extend(["file_json", "error_file"])

    handlers_config: Dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
    }

    if enable_file_logging:
        handlers_config["file_json"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json",
            "filename": f"{log_dir}/app.log",
            "maxBytes": max_bytes,
            "backupCount": backup_count,
            "encoding": "utf-8",
        }
        handlers_config["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": f"{log_dir}/error.log",
            "maxBytes": max_bytes,
            "backupCount": backup_count,
            "encoding": "utf-8",
        }

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {"()": JsonFormatter},
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": handlers_config,
        "loggers": {
            "app": {
                "handlers": handlers_list,
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": handlers_list if enable_file_logging else ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": handlers_list if enable_file_logging else ["console"],
                "level": "WARNING",  # Only show access errors - can change this!
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": error_handlers_list,
                "level": "INFO",
                "propagate": False,
            },
            "httpx": {
                "handlers": handlers_list if enable_file_logging else ["console"],
                "level": "WARNING",  # Only show HTTP errors - can change this as well!
                "propagate": False,
            },
        },
        "root": {
            "handlers": handlers_list if enable_file_logging else ["console"],
            "level": log_level,
        },
    }

    dictConfig(log_config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: The name for the logger (typically __name__)

    Returns:
        A configured logger instance
    """
    if not name.startswith("uvicorn") and name != "__main__":
        name = f"app.{name}"
    return logging.getLogger(name)
