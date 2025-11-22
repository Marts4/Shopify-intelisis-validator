"""
Decoradores útiles para retry, timing y logging automático.
Mejoran la robustez y observabilidad del sistema.
"""

import time
import functools
from typing import Callable, Type, Tuple
from .logger import get_logger

logger = get_logger('DECORATORS')


def retry(max_attempts: int = 3, delay: float = 1.0, 
          backoff: float = 2.0, exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    Decorador para reintentar una función en caso de error.
    
    Args:
        max_attempts: Número máximo de intentos
        delay: Delay inicial entre intentos (segundos)
        backoff: Factor multiplicador del delay en cada intento
        exceptions: Tupla de excepciones a capturar
    
    Ejemplo:
        @retry(max_attempts=3, delay=2.0, exceptions=(requests.RequestException,))
        def fetch_data():
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} falló después de {max_attempts} intentos",
                            exc_info=True
                        )
                        raise
                    
                    logger.warning(
                        f"{func.__name__} falló (intento {attempt}/{max_attempts}). "
                        f"Reintentando en {current_delay}s..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # No debería llegar aquí, pero por seguridad
            raise last_exception
        
        return wrapper
    return decorator


def timing(operation_name: str = None):
    """
    Decorador para medir tiempo de ejecución de una función.
    
    Args:
        operation_name: Nombre descriptivo de la operación (opcional)
    
    Ejemplo:
        @timing("Fetch Orders from Shopify")
        def get_orders():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            
            logger.debug(f"Iniciando: {name}")
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.info(
                    f"Completado: {name} (⏱️ {elapsed:.2f}s)",
                    operation="TIMING"
                )
                
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"Falló: {name} después de {elapsed:.2f}s",
                    operation="TIMING",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_call(level: str = 'DEBUG'):
    """
    Decorador para registrar llamadas a funciones automáticamente.
    
    Args:
        level: Nivel de log ('DEBUG', 'INFO', 'WARNING', etc.)
    
    Ejemplo:
        @log_call(level='INFO')
        def process_order(order_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Construir mensaje con argumentos
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            
            log_method = getattr(logger, level.lower(), logger.debug)
            log_method(f"Llamando {func.__name__}({signature})")
            
            try:
                result = func(*args, **kwargs)
                log_method(f"{func.__name__} completado exitosamente")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} falló: {str(e)}", exc_info=True)
                raise
        
        return wrapper
    return decorator


def handle_errors(default_return=None, log_level: str = 'ERROR'):
    """
    Decorador para capturar y registrar errores sin interrumpir el flujo.
    Útil para operaciones no críticas.
    
    Args:
        default_return: Valor a retornar en caso de error
        log_level: Nivel de log para el error
    
    Ejemplo:
        @handle_errors(default_return=[])
        def fetch_optional_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_method = getattr(logger, log_level.lower(), logger.error)
                log_method(
                    f"Error en {func.__name__}: {str(e)}. "
                    f"Retornando valor por defecto: {default_return}",
                    exc_info=True
                )
                return default_return
        
        return wrapper
    return decorator