"""
VIP检查类
利用VIP来实现HA
"""
from handler import *
from logger.Fun_log_create import  *
from global_vars.Class_global_vars import *
from my_exception.exception import *
from tool import *
import time
import sys

__all__ = ['vipha']

class vipha(Handller):
    """实现类"""
    def __init__(self):
        self.logger = None #日志系统指针
        self.options = None #全局参数指针
        self.set_var = None #高阶函数指针 用于设置一个全局参数
        self.get_var = None #高阶函数指针 用于获取一个全局参数
        self.local_ip = None #本地IP
        self.option_keys = ["vip", "mgr_seeds", "gateway", "mysql_port", "mgr_port", \
                "user", "passwd", "sleeptime", "logdir", "lock_file", "stat_file", "log_level"] #可用选项列表
    def vars_init(self, vars):
        '''
        本函数初始化各种参数包括日志系统、将解析的参数加入到全局参数
        :param  vars: 解析命令行得到的参数为一个key-value字典
        :return: 1 err 0 ok
        '''
        self.set_var = global_var.set_global_vars
        self.get_var = global_var.get_global_vars
        self.options = global_var.get_all_global_vars()
        self.logger =  self.get_var("logger")

        if isinstance(vars, dict) != 1:
            raise Data_type_err("dict require but type is {}".format(type(vars)))
            return 1

        for var in vars: #初始化全部参数变量到全集变量字典
            self.set_var(var, vars[var])

        self.logger.info("vars_init: All options [INIT] complete!! is:")

        for i in (self.options):
            if i == 'passwd':
                pass
            else:
                self.logger.info("options {} values is {}".format(i, self.options[i]))


        self.set_var("eret", "unkown return, or unkown error") #这里只是增加到全局参数列表便于方便书写
        return 0

    def check_stat(self):
        """
        主检查函数，通过检查后还需要进一步判断VIP是否已经启动来最终判断是否需要进一步处理VIP（绑定、解绑、不变）
        VIP检查函数见后面，这样做是为了让本函数支持keepalived检查
        返回值
            0=>状态检查成功，需要绑定VIP
            1=>状态检查失败，需要关闭VIP
        """

        # [STAGE1]:
        # 检查本机IP是否在集群中
        # 检查方法:通过获取本机的网卡地址和网卡名称和参数字典mgr_seeds中的值网卡地址和名称进行对比
        # 如果在则继续
        # 如果不在则 return 1
        # check_localip_in_mgr 函数成功放回本机IP地址,失败返回 1
        self.local_ip = check_localip_in_mgr(self.logger, self.get_var('mgr_seeds'))
        if self.local_ip != 1 :
            self.logger.info("check_stat:[STAGE1] local_ip:{} check succ!" . format(self.local_ip))
        else:
            self.logger.info("check_stat:[STAGE1] check failed, local_ip:{} \
                    not in mgr cluster:{}..." . format(self.local_ip,self.get_var('mgr_seeds')))
            return 1

        # [STAGE2]:
        # 检查mysqld是否启动 检查方法:1、端口是否可用 2、mysqld是否可以连接
        # 如果启动则继续
        # 如果没有启动则 return 1
        # connect_mysqld 函数成功返回0,失败返回1
        if connect_mysqld(self.logger, self.local_ip, self.get_var('mysql_port'), self.get_var('user'), self.get_var('passwd')) == 0:
            self.logger.info("check_stat:[STAGE2] mysqld {}:{} connect scuess!" . \
                    format(self.local_ip, self.get_var('mysql_port')))
        else:
            self.logger.info("check_stat:[STAGE2] mysqld {}:{} connect failed..." . \
                    format(self.local_ip, self.get_var('mysql_port')))
            return 1

        # [STAGE3]:
        # 检查MGR是否启动以及是否是本节点是主
        # 检查方法:
        #   1、检查MGR的paxos通信端口是否可用
        #   2、检查本机是否在MGR中且为online
        #   3、通过脚本检查本节点是否是MGR的主节点
        # 如果是则继续
        # 如果不是则 return 1
        # check_mgr_primary 函数成功返回0,失败返回1
        if check_mgr_primary(self.logger, self.local_ip, self.get_var('mgr_port'), self.get_var('mysql_port'), \
                self.get_var('user'), self.get_var('passwd')) == 0:
            self.logger.info("check_stat:[STAGE3] {} is mgr primary!" . format(self.local_ip))
        else:
            self.logger.info("check_stat:[STAGE3] {} not mgr primary..." . format(self.local_ip))
            return 1

        # [STAGE4]
        # 检查最后一种情况：如果出现了网络断开的情况
        # 测试中这情况根据语句会查出2个主，但是不满足大多数节点的部分不能进行事务，因为收到不到
        # 回执的tickets，事务会一直hang住, 因此数据不用担心，但是作为VIP检测程序还是需要判断这种情况，
        # 因为我们的服务器都是通过路由器连接因此可以简单的检测到网关的连通性。
        # 检查网络断开
        # 检查方法：检查网关的连通性
        # 如果连通则继续
        # 否则 return 1
        # gateway_connectable 函数成功返回0,失败返回1
        if gateway_connectable(self.logger, self.get_var('gateway')) == 0:
            self.logger.info("check_stat:[STAGE4] check gatway:{} sucess!" . format(self.get_var('gateway')))
        else:
            self.logger.info("check_stat:[STAGE4] check gatway:{} failed..." . format(self.get_var('gateway')))
            return 1


        #最后，4个阶段检查全部通过，返回0，表示正常
        return 0

    def check_vip(self, check_stat):
        """
        根据check_stat()的返回值，决定后续VIP该如何操作（绑定、不变、解绑）
        - param: stat => check_stat()函数的返回值
        - return:
            0 => 关闭
            1 => 维持
            2 => 启动
        """

        # 检查VIP是否绑定在当前主机上，返回值：
        #   0 => vip绑定在本地
        #   1 => vip未绑定在本地
        vip_bind_stat = check_vip_local_bound(self.logger, self.get_var('vip'))

        # check_stat = 0 => 状态检查成功，需要绑定VIP
        if check_stat == 0:  #如果需要启动VIP
            self.logger.info("check_vip: vip should be bound")

            # 已绑定，则维持现状即可
            if vip_bind_stat == 0:
                self.logger.info("check_vip: vip had been bound...")
                return 1

            #如果不在本地
            elif vip_bind_stat == 1:
                self.logger.info("check_vip: vip not been bound, test for connectivity")

                # 如果还能ping通VIP，则本次循环维持现状，等待下次循环再检测，先维持现状
                # 这里还避免一种网络问题导致MGR分块的恢复网络后的问题
                if not(ip_connectable(self.logger,self.get_var('vip'))) :
                    self.logger.warning("check_vip: vip connectable, will retry next time...")
                    return 1

                # 下面做二次检查因为启动VIP是重要事件
                self.logger.warning("check_vip: check again vip connectable before starting vip")

                # 二次检查失败，先不绑定VIP，先维持现状
                if self.check_stat() != 0:
                    self.logger.info("check_vip: check again failed, will not start vip...")
                    return 1

                # VIP未绑定本地，且ping不同，则可以启动VIP
                return 2

            #其他返回值，意外错误情况
            else:
                self.logger.error("check_vip[1]:" + self.get_var("eret"))
                exit(-1)

        # check_stat = 1 => 状态检查失败，需要关闭VIP
        if check_stat == 1:
            self.logger.info("check_vip: vip should not be bound...")

            # 本地是否已解绑VIP
            # 如果在本地，则需要解绑
            if vip_bind_stat == 0:
                self.logger.info("check_vip: vip had been bound, and should be unbound...")
                self.logger.warning("check_vip: check again before unbound vip...")
                # 再次检查，发现不需要解绑了，则维持现状
                if self.check_stat() != 1:
                    self.logger.info("check_vip: check again to stop vip failed, will check next time...")
                    return 1
                # 否则需要解绑VIP
                return 0

            # 如果未绑定VIP，则无需解绑，维持现状
            elif vip_bind_stat == 1:
                self.logger.info("check_vip:vip {} not on this node, do nothing" . format(self.get_var('vip')))
                return 1

            #其他返回值，意外错误情况
            else:
                self.logger.error("check_vip[2]:" + self.get_var("eret"))
                exit(-1)

        #其他返回值，意外错误情况
        if check_stat not in (0,1):
            self.logger.error("check_vip[3]:" + self.get_var("eret"))
            exit(-1)

    def set_vip(self, vip_stat):
        """
        根据MGR状态检查结果(check_stat())，及VIP检查结果(check_vip())，决定接下来VIP的操作动作（0=>关闭，1=>维持，2=>启动)
        - param: vip_stat => check_vip()返回的状态值
        - return: 没有返回值
        """

        """
        vip_stat:
            0 => 关闭
            1 => 维持
            2 => 启动
        """
        # 关闭VIP
        if vip_stat == 0:
            # 修改stat_file状态值
            stat_file_fd = self.get_var("stat_file_fd")
            stat_file_fd.seek(0,0)
            stat_file_fd.write("0")
            stat_file_fd.flush()

            # 关闭VIP
            if unbind_vip(self.logger, self.get_var('vip'), self.local_ip) == 0:
                self.logger.warning("set_vip: vip:{} unbound!" . format(self.get_var('vip')))
            else:
                #如果失败继续循环
                pass

        # 维持不变
        elif vip_stat == 1:
            self.logger.info("set_vip: do nothing")

        # 启动VIP
        elif vip_stat == 2:
            # 修改stat_file状态值
            stat_file_fd = self.get_var("stat_file_fd")
            stat_file_fd.seek(0,0)
            stat_file_fd.write("2")
            stat_file_fd.flush()

            # 启动VIP
            if bind_vip(self.logger, self.get_var('vip'), self.local_ip) == 0:
                self.logger.warning("set_vip: vip:{} bound on:{}" . format(self.get_var('vip'), self.local_ip))
            else:
                #绑定失败则继续循环操作
                pass
        # 其他情况
        else:
            self.logger.error("set_vip[1]:" + self.get_var("eret"))
            exit(-1)


    def check_vars(self, vars):
        """
        检查参数列表是否合规
        - param: vars => 待检查的参数字典
        - return: 没有返回值
        """
        # config.py里定义的参数列表，和self.option_keys定义的列表数量对不上
        if len(vars) != len(self.option_keys):
            self.logger.error("check_vars: vars number out of range")
            exit(-1)

        # 逐个检查所有参数是否在参数列表中
        for i in vars:
            # 检查参数名是否一一对应
            if i not in self.option_keys:
                self.logger.error("check_vars: key:{} is out of range..." . format(i))
                exit(-1)

            # 检查参数名是否都为string
            if isinstance(i, str) != 1:
                self.logger.error("check_vars: key:{} type not [string]..." . format(i))
                exit(-1)

            # mgr_seeds的值必须是dict类型
            if i == 'mgr_seeds':
                if isinstance(vars[i], dict) != 1:
                    self.logger.error("check_vars: key:{}/{} type not [dict]..." . format(i, type(vars[i])))
                    exit(-1)

            # sleeptime的值必须是int类型
            elif i == "sleeptime":
                if isinstance(vars[i], int) != 1:
                    self.logger.error("check_vars: key:{}/{} type not [int]..." . format(i, type(vars[i])))
                    exit(-1)
            else:
                # 其他类型都必须是string
                if isinstance(vars[i], str) != 1:
                    self.logger.error("check_vars: key:{}/{} type not [string]..." . format(i, type(vars[i])))
                    exit(-1)

            # 检查 logdir 参数值
            if  i == 'logdir':
                # 必须以 '/' 结尾
                if vars['logdir'][-1:] != '/':
                    self.logger.error("check_vars: logdir:{} should be end with '/'" . format(vars['logdir']))
                    sys.stdout.flush()
                    exit(-1)

        return
