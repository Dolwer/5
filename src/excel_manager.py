import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
import shutil
from typing import Dict

class ExcelManager:
    """
    Класс для работы с Excel-файлом, включая загрузку, проверку структуры, обновление строк, 
    сохранение изменений и создание резервных копий.
    """
    def __init__(self, config: Dict, stats) -> None:
        """
        Инициализация ExcelManager.

        Args:
            config (Dict): Конфигурация из файла config.yaml.
            stats: Объект для сбора статистики.
        """
        self.file_path = Path(config["excel"]["path"])
        self.backup_enabled = config["excel"]["backup"].get("enabled", True)
        self.backup_keep_days = config["excel"]["backup"].get("keep_days", 7)
        self.columns = config["excel"]["columns"]
        self.required_columns = list(self.columns.values())
        self.target_columns = config["excel"]["target_columns"]
        self.stats = stats
        self.logger = logging.getLogger("main")
        self.data = None  # DataFrame с содержимым Excel-файла

    def check_structure(self) -> None:
        """
        Проверяет наличие Excel-файла и его структуру.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")
        self.logger.info(f"Excel file found: {self.file_path}")

        # Проверка структуры столбцов
        temp_data = pd.read_excel(self.file_path, nrows=1, dtype=str)
        missing_columns = [col for col in self.required_columns if col not in temp_data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns in Excel file: {', '.join(missing_columns)}")
        self.logger.info("Excel file structure is valid.")

    def load_data(self) -> None:
        """
        Загружает данные из Excel-файла в DataFrame.
        """
        try:
            self.data = pd.read_excel(self.file_path, dtype=str).fillna("")
            self.logger.info(f"Loaded {len(self.data)} rows from Excel file.")
        except Exception as e:
            self.logger.error(f"Failed to load Excel file: {str(e)}")
            raise

    def update_data(self, email: str, thread_data: Dict, analysis_results: Dict) -> None:
        """
        Обновляет строки в Excel-файле на основе данных анализа.

        Args:
            email (str): Адрес электронной почты, на который отправлено письмо.
            thread_data (Dict): Данные о переписке.
            analysis_results (Dict): Результаты анализа письма.
        """
        try:
            # Найти строки по email (столбец Mail)
            matching_rows = self.data[self.data[self.columns["mail"]].str.lower() == email.lower()]
            if matching_rows.empty:
                self.logger.warning(f"No matching row found for email: {email}")
                return

            # Обновляем значения в столбцах
            for index, row in matching_rows.iterrows():
                for target_column in self.target_columns:
                    if target_column in analysis_results:
                        old_value = self.data.at[index, self.columns[target_column]]
                        new_value = analysis_results[target_column]
                        if old_value != new_value:
                            self.data.at[index, self.columns[target_column]] = new_value
                            self.logger.info(
                                f"Updated row {index} for column {target_column}: {old_value} -> {new_value}"
                            )

            self.stats.updated_rows += len(matching_rows)
        except Exception as e:
            self.logger.error(f"Failed to update Excel data for email {email}: {str(e)}")
            self.stats.errors += 1
            raise

    def save_data(self) -> None:
        """
        Сохраняет изменения обратно в Excel-файл.
        """
        try:
            self.data.to_excel(self.file_path, index=False)
            self.logger.info(f"Excel file saved successfully: {self.file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save Excel file: {str(e)}")
            raise

    def create_backup(self) -> None:
        """
        Создает резервную копию Excel-файла.
        """
        if not self.backup_enabled:
            self.logger.info("Backup creation is disabled in configuration.")
            return

        try:
            backup_dir = self.file_path.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_file = backup_dir / f"{self.file_path.stem}_backup_{timestamp}.xlsx"
            shutil.copy(self.file_path, backup_file)
            self.logger.info(f"Backup created: {backup_file}")

            # Удаление старых резервных копий
            self.cleanup_old_backups(backup_dir)
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            raise

    def cleanup_old_backups(self, backup_dir: Path) -> None:
        """
        Удаляет старые резервные копии, которые превышают допустимое количество дней.

        Args:
            backup_dir (Path): Папка с резервными копиями.
        """
        try:
            for backup_file in backup_dir.iterdir():
                if backup_file.is_file():
                    file_age_days = (datetime.now() - datetime.fromtimestamp(backup_file.stat().st_mtime)).days
                    if file_age_days > self.backup_keep_days:
                        backup_file.unlink()
                        self.logger.info(f"Deleted old backup: {backup_file}")
        except Exception as e:
            self.logger.error(f"Failed to clean up old backups: {str(e)}")
            raise
