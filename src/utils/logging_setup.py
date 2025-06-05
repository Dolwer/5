import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(config: dict = None) -> logging.Logger:
    """
    Настраивает систему логирования с поддержкой ротации логов.
    
    Args:
        config (dict): Конфигурация логирования из config.yaml.
    
    Returns:
        logging.Logger: Инициализированный логгер.
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)  # Создаём директорию для логов, если её нет.

    # Настройка лог-файла
    log_file = log_dir / "app.log"

    # Определяем уровень логирования
    log_level = logging.INFO
    if config and "level" in config:
        log_level = getattr(logging, config["level"].upper(), logging.INFO)

    # Настройка ротации логов
    max_size = config.get("max_size", 1024 * 1024) if config else 1024 * 1024  # 1MB по умолчанию
    backup_count = config.get("backup_count", 5) if config else 5  # 5 резервных копий по умолчанию

    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=backup_count
    )

    # Настройка формата логов
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    )
    handler.setFormatter(formatter)

    # Настройка глобального логгера
    logger = logging.getLogger("main")
    logger.setLevel(log_level)
    logger.addHandler(handler)

    # Также добавляем вывод логов в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("Logging system initialized.")
    return logger
