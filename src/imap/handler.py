import imaplib
import email
from typing import List, Dict, Optional
import logging
from email.utils import parseaddr

class IMAPHandler:
    """
    Класс для обработки IMAP-соединения и работы с почтовым сервером, 
    включая анализ отправленных писем и их ответов.
    """
    def __init__(self, config: Dict, stats) -> None:
        """
        Инициализация IMAPHandler.

        Args:
            config (Dict): Конфигурация IMAP из config.yaml.
            stats: Объект для сбора статистики.
        """
        self.config = config["imap"]
        self.stats = stats
        self.connection = None
        self.logger = logging.getLogger("main")

    def connect(self) -> None:
        """
        Устанавливает соединение с IMAP-сервером.
        """
        try:
            self.connection = imaplib.IMAP4_SSL(self.config["host"], self.config["port"])
            self.connection.login(self.config["username"], self.config["password"])
            self.logger.info("Successfully connected to IMAP server.")
        except imaplib.IMAP4.error as e:
            self.logger.error(f"Failed to connect to IMAP server: {str(e)}")
            raise

    def fetch_sent_emails(self) -> List[Dict]:
        """
        Получает все отправленные письма из папки "Sent".

        Returns:
            List[Dict]: Список словарей с данными о письмах.
        """
        try:
            self.connection.select('"[Gmail]/Sent Mail"' if "gmail" in self.config["host"].lower() else "Sent")
            status, messages = self.connection.search(None, "ALL")
            if status != "OK":
                self.logger.warning("No sent emails found.")
                return []

            email_ids = messages[0].split()
            sent_emails = []
            for email_id in email_ids:
                status, data = self.connection.fetch(email_id, "(RFC822)")
                if status != "OK":
                    self.logger.error(f"Failed to fetch email with ID {email_id.decode()}")
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                sent_emails.append(self._parse_email(msg, email_id.decode()))
                self.stats.processed_emails += 1

            self.logger.info(f"Fetched {len(sent_emails)} sent emails.")
            return sent_emails
        except Exception as e:
            self.logger.error(f"Error while fetching sent emails: {str(e)}")
            self.stats.errors += 1
            return []

    def fetch_replies(self, sent_email: Dict) -> List[Dict]:
        """
        Ищет ответы на конкретное отправленное письмо.

        Args:
            sent_email (Dict): Словарь с данными об отправленном письме.

        Returns:
            List[Dict]: Список словарей с данными о найденных ответах.
        """
        try:
            # Фильтр по заголовку "In-Reply-To" или "References"
            self.connection.select(self.config["folder"])
            status, messages = self.connection.search(None, f'HEADER "References" "{sent_email["message_id"]}"')
            if status != "OK":
                self.logger.warning(f"No replies found for sent email ID {sent_email['id']}")
                return []

            email_ids = messages[0].split()
            replies = []
            for email_id in email_ids:
                status, data = self.connection.fetch(email_id, "(RFC822)")
                if status != "OK":
                    self.logger.error(f"Failed to fetch reply email with ID {email_id.decode()}")
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                replies.append(self._parse_email(msg, email_id.decode()))
                self.stats.processed_emails += 1

            self.logger.info(f"Found {len(replies)} replies for sent email ID {sent_email['id']}.")
            return replies
        except Exception as e:
            self.logger.error(f"Error while fetching replies for sent email: {str(e)}")
            self.stats.errors += 1
            return []

    def _parse_email(self, msg: email.message.EmailMessage, email_id: str) -> Dict:
        """
        Парсит письмо и извлекает ключевые данные.

        Args:
            msg (email.message.EmailMessage): Объект письма.
            email_id (str): ID письма.

        Returns:
            Dict: Словарь с данными о письме.
        """
        try:
            subject = msg["subject"]
            sender = parseaddr(msg["from"])[1]
            recipient = parseaddr(msg["to"])[1]
            message_id = msg["Message-ID"]
            body = self._get_email_body(msg)
            return {
                "id": email_id,
                "subject": subject,
                "from": sender,
                "to": recipient,
                "message_id": message_id,
                "body": body,
            }
        except Exception as e:
            self.logger.error(f"Failed to parse email {email_id}: {str(e)}")
            self.stats.errors += 1
            return {}

    def _get_email_body(self, msg: email.message.EmailMessage) -> str:
        """
        Извлекает тело письма (plain text или HTML).

        Args:
            msg (email.message.EmailMessage): Объект письма.

        Returns:
            str: Тело письма в виде строки.
        """
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        return part.get_payload(decode=True).decode()
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        return part.get_payload(decode=True).decode()
            else:
                return msg.get_payload(decode=True).decode()
        except Exception as e:
            self.logger.error(f"Failed to extract email body: {str(e)}")
            self.stats.errors += 1
            return ""

    def disconnect(self) -> None:
        """
        Закрывает соединение с IMAP-сервером.
        """
        try:
            if self.connection:
                self.connection.close()
                self.connection.logout()
                self.logger.info("Disconnected from IMAP server.")
        except Exception as e:
            self.logger.error(f"Error while disconnecting from IMAP server: {str(e)}")
