import logging
import traceback
from  global_vars.Class_global_vars import *

__all__ = ['create_logging']
def create_logging(file_name,name):
    try:
        if isinstance(name, str) != 1:
            raise TypeError
    except Exception:
        traceback.print_exc()
        exit()

    ##定义日志格式
    if global_var.get_global_vars('log_level'):
        logger = logging.getLogger(name)
        logger.setLevel(level = global_var.get_global_vars('log_level'))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logger = logging.getLogger(__name__)
        logger.setLevel(level = logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s file:%(filename)s line:%(lineno)d fun:%(funcName)s')
    ##设置日志打印
    handler = logging.FileHandler(file_name)
    if global_var.get_global_vars('log_level'):
        handler.setLevel(level = global_var.get_global_vars('log_level'))
    else:
        handler.setLevel(level = logging.INFO)
    handler.setFormatter(formatter)

    ##定义控制台输出
    console = logging.StreamHandler()
    if global_var.get_global_vars('log_level'):
        console.setLevel(level = global_var.get_global_vars('log_level'))
    else:
        console.setLevel(level = logging.INFO)
    console.setFormatter(formatter)

    ##为longger增加2种输出
    logger.addHandler(handler)
    #logger.addHandler(console)

    logger.info("Longger System Create Finish")
    return logger
