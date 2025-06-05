class ProcessingStats:
    """
    Класс для отслеживания статистики обработки писем и изменений в Excel.
    """
    def __init__(self):
        self.processed_emails = 0  # Количество успешно обработанных писем
        self.updated_rows = 0      # Количество обновлённых строк в Excel
        self.errors = 0            # Количество ошибок

    def log_summary(self):
        """
        Логирует сводку статистики обработки.
        """
        print(f"Processed emails: {self.processed_emails}")
        print(f"Updated Excel rows: {self.updated_rows}")
        print(f"Errors encountered: {self.errors}")
