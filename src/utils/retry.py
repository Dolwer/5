Args:
    max_attempts (int): Максимальное количество попыток.
    exception_to_check (Tuple[Type[Exception], ...]): Исключения, которые следует перехватывать для повторного вызова.
    base_delay (float): Начальная задержка перед повторным вызовом (в секундах).
    backoff_factor (float): Множитель для увеличения времени задержки при каждом повторе.
    logger (logging.Logger): Логгер для записи информации о попытках и ошибках.

Returns:
    Callable: Обёрнутая функция с логикой повторных вызовов.
"""
def decorator_retry(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        attempts = 0
        delay = base_delay
        while attempts < max_attempts:
            try:
                return func(*args, **kwargs)
            except exception_to_check as e:
                attempts += 1
                if logger:
                    logger.warning(
                        f"Attempt {attempts} failed with exception: {e}. Retrying in {delay} seconds..."
                    )
                if attempts >= max_attempts:
                    if logger:
                        logger.error(f"All {max_attempts} attempts failed. Raising exception.")
                    raise
                time.sleep(delay)
                delay *= backoff_factor
    return wrapper
return decorator_retry
