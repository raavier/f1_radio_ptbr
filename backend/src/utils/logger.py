import logging
import sys
from datetime import datetime
import os

def get_logger(name: str) -> logging.Logger:
    """Cria e configura um logger"""
    
    logger = logging.getLogger(name)
    
    # Evita duplicar handlers se o logger já foi configurado
    if logger.handlers:
        return logger
    
    # Define o nível de log baseado na variável de ambiente
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Formato das mensagens
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo (opcional)
    if os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true":
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(
            f"{log_dir}/f1_radio_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger