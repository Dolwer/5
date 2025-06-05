import requests
import logging
from typing import Dict, Any

class LMStudioClient:
    """
    Клиент для взаимодействия с LM Studio API.
    """
    def __init__(self, config: Dict) -> None:
        """
        Инициализация клиента LM Studio.

        Args:
            config (Dict): Конфигурация из файла config.yaml.
        """
        self.base_url = config["lm_studio"]["base_url"]
        self.api_key = config["lm_studio"]["api_key"]
        self.timeout = config["lm_studio"].get("timeout", 30)
        self.logger = logging.getLogger("main")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def analyze_text(self, text: str, model: str) -> Dict[str, Any]:
        """
        Анализирует текст с помощью LM Studio API.

        Args:
            text (str): Текст для анализа.
            model (str): Название модели, используемой для анализа.

        Returns:
            Dict[str, Any]: Результат анализа текста, возвращённый API.
        """
        endpoint = f"{self.base_url}/analyze"
        payload = {
            "text": text,
            "model": model
        }

        try:
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            # Логирование успешного ответа
            self.logger.info(f"Text analysis successful: {result}")
            return result

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error during text analysis: {str(e)}")
            raise

    def health_check(self) -> bool:
        """
        Проверяет доступность API.

        Returns:
            bool: True, если API доступно, иначе False.
        """
        endpoint = f"{self.base_url}/health"

        try:
            response = requests.get(endpoint, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            # Логирование успешного ответа
            self.logger.info("API health check successful.")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API health check failed: {str(e)}")
            return False
