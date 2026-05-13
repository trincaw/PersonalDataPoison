from __future__ import annotations

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

import structlog

DEFAULT_LOG_DIR = "data/telemetry"


def setup_logging(config: dict[str, Any] | None = None) -> None:
    cfg = config or {}
    level = cfg.get("level", "INFO")
    log_dir = Path(cfg.get("log_dir", DEFAULT_LOG_DIR))
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / cfg.get("filename", "pdp.log")

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
                "level": level,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": str(log_file),
                "maxBytes": cfg.get("max_bytes", 10_485_760),
                "backupCount": cfg.get("backup_count", 5),
                "level": "DEBUG",
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
        },
        "loggers": {
            "playwright": {"level": "WARNING"},
            "aiohttp": {"level": "WARNING"},
            "sqlalchemy": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(logging_config)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.getLogger(__name__).info("Logging initialized (level=%s, file=%s)", level, log_file)
