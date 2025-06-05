#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict
from datetime import datetime, timezone

# Загрузка переменных окружения из файла .env
load_dotenv()

# Добавляем корневую директорию в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# Импорты из локального кода
from src.utils.logging_setup import setup_logging
from src.utils.stats import ProcessingStats
from src.imap.handler import IMAPHandler
from src.excel_manager import ExcelManager
from src.lm_studio_client import LMStudioClient
import yaml

# Константы
CURRENT_USER = os.getenv("USERNAME", "Dolwer")
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

def get_current_utc() -> str:
    """
    Получение текущего времени в UTC формате.
    """
    return datetime.now(timezone.utc).strftime(DATETIME_FORMAT)

def load_config() -> Dict:
    """
    Загрузка конфигурации из файла config.yaml с поддержкой переменных окружения.

    Returns:
        Dict: Загруженная конфигурация

    Raises:
        FileNotFoundError: Если файл конфигурации или Excel файл не найден.
        yaml.YAMLError: Если возникла ошибка парсинга файла конфигурации.
    """
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)

        # Проверка обязательных секций
        required_sections = ["excel", "imap", "lm_studio", "logging", "user"]
        missing_sections = [section for section in required_sections if section not in config]
        if missing_sections:
            raise ValueError(f"Missing required config sections: {', '.join(missing_sections)}")

        # Подстановка переменных окружения
        config["imap"]["username"] = os.getenv("ZOHO_EMAIL", config["imap"].get("username", ""))
        config["imap"]["password"] = os.getenv("ZOHO_APP_PASSWORD", config["imap"].get("password", ""))
        config["excel"]["path"] = os.getenv("EXCEL_FILE_PATH", config["excel"].get("path", ""))
        config["lm_studio"]["host"] = os.getenv("LMSTUDIO_HOST", config["lm_studio"].get("host", "localhost"))
        config["lm_studio"]["port"] = os.getenv("LMSTUDIO_PORT", config["lm_studio"].get("port", 1234))
        config["lm_studio"]["version"] = os.getenv("LMSTUDIO_VERSION", config["lm_studio"].get("version", ""))

        # Проверка пути к Excel файлу
        excel_path = config["excel"]["path"]
        if not excel_path or not Path(excel_path).exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        return config
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse config file: {str(e)}")

def process_emails(imap_handler: IMAPHandler, 
                   excel_manager: ExcelManager, 
                   lm_studio_client: LMStudioClient, 
                   stats: ProcessingStats) -> None:
    """
    Обработка писем и обновление данных в Excel файле.

    Args:
        imap_handler (IMAPHandler): Обработчик IMAP сообщений.
        excel_manager (ExcelManager): Менеджер Excel файла.
        lm_studio_client (LMStudioClient): Клиент для взаимодействия с LM Studio.
        stats (ProcessingStats): Объект для сбора статистики.
    """
    logger = logging.getLogger("main")
    logger.info(f"Starting email processing at {get_current_utc()} UTC")
    logger.info(f"Processing as user: {CURRENT_USER}")

    try:
        for thread in imap_handler.get_email_threads():
            for message in thread["messages"]:
                if message.get("processed"):
                    continue

                analysis_result = lm_studio_client.analyze_email(
                    email_body=message["body"],
                    context=thread.get("context")
                )

                if "error" in analysis_result:
                    logger.error(f"Analysis failed: {analysis_result['error']}")
                    continue

                excel_manager.update_data(
                    email=message["from"],
                    thread_data=thread,
                    analysis_results=analysis_result
                )

                imap_handler.mark_as_read(message["message_id"])
                stats.processed_emails += 1
    except Exception as e:
        logger.error(f"Error during email processing: {str(e)}")
        stats.errors += 1
        raise

def main() -> None:
    """
    Основная функция запуска приложения.
    """
    logger = setup_logging()
    stats = ProcessingStats()

    try:
        # Загрузка конфигурации
        config = load_config()

        # Инициализация компонентов
        excel_manager = ExcelManager(config, stats)
        imap_handler = IMAPHandler(config, stats)
        lm_studio_client = LMStudioClient(config)

        # Проверка и загрузка Excel файла
        excel_manager.check_structure()
        excel_manager.load_data()

        # Обработка писем
        process_emails(imap_handler, excel_manager, lm_studio_client, stats)

        # Сохранение изменений в Excel
        excel_manager.save_data()
        stats.log_summary()

        logger.info("Processing completed successfully.")
    except FileNotFoundError as fnf_error:
        logger.critical(f"Critical error: {fnf_error}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
