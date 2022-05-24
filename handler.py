"""
这是接口类
2018-12-21
"""

from abc import ABC, abstractmethod
from logger.Fun_log_create import  *
from global_vars.Class_global_vars import *

__all__ = ['Handller','Worker']

class Handller(ABC):
    """
    抽象接口
    """
    @abstractmethod
    def vars_init(self, log_level, vars):
        """
        接口函数用于初始化各种子模块
        :return: 0 错误 1 正常
        """
        pass
    def check_stat(self):
        """
        接口函数用于检查所有的状态
        :return: 0 正常 1 失败
        """
        pass

    def check_vip(self,stat):
        """
        检查VIP的函数接口
        :return: 0 关闭 1 维持 2 启动
        """
        pass

    def set_vip(self,stat):
        """
        启动VIP的函数接口
        :return:
        """
        pass

    def check_vars(self,vars):
        """
        检查参数接口
        :param vars:
        :return:
        """
        pass


class Worker():
    """
    调用类，做相应的解耦
    """
    def __init__(self,handler):
        self.vip_handler = handler
        self.logger = None

    def vars_init(self, log_level, vars):
        """
        环境初始化辅助类主要用于初始化日志系统
        :param log_level: 日志级别
        :param vars: 自定义的环境变量字典列表
        :return: 无返回值
        """
        #下面初始化日志系统模块
        global_var.set_global_vars('log_level', vars['log_level'])
        self.logger = create_logging((vars['logdir']+'GreatSQLHA.log'), "GreatSQLHA")
        global_var.set_global_vars('logger', self.logger)

        #下面初始化其他参数
        try:
            self.vip_handler.vars_init(vars)
        except Exception as e:
            self.logger.error(e,exc_info = True)
            exit(-1) #异常退出

    def check_stat(self):  #检查基本状态 4 阶段
        return self.vip_handler.check_stat()

    def check_vip(self,stat):#检查VIP状态
        return self.vip_handler.check_vip(stat)

    def set_vip(self,stat): #做vip操作
        return self.vip_handler.set_vip(stat)

    def check_vars(self,vars): #进行参数检查
        self.vip_handler.check_vars(vars)
