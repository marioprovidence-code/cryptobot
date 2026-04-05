from datetime import datetime
from pathlib import Path

import logging_utils


def _cleanup(logger):
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def test_get_logger_creates_rotating_handler(tmp_path, monkeypatch):
    monkeypatch.setattr(logging_utils, "LOG_DIR", str(tmp_path))
    logger = logging_utils.get_logger("unit-test-rotating", max_bytes=123, backup_count=7)
    try:
        assert len(logger.handlers) == 2
        file_handler = next(
            handler
            for handler in logger.handlers
            if isinstance(handler, logging_utils.RotatingFileHandler)
        )
        assert Path(file_handler.baseFilename).parent == tmp_path
        expected_name = f"cryptobot_{datetime.now().strftime('%Y-%m-%d')}.log"
        assert Path(file_handler.baseFilename).name == expected_name
        assert file_handler.maxBytes == 123
        assert file_handler.backupCount == 7
    finally:
        _cleanup(logger)


def test_get_logger_reuses_existing_handlers(tmp_path, monkeypatch):
    monkeypatch.setattr(logging_utils, "LOG_DIR", str(tmp_path))
    name = "unit-test-reuse"
    logger = logging_utils.get_logger(name)
    try:
        handler_ids = tuple(id(handler) for handler in logger.handlers)
        logger_again = logging_utils.get_logger(name)
        assert tuple(id(handler) for handler in logger_again.handlers) == handler_ids
    finally:
        _cleanup(logger)
