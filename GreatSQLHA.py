"""
GreatSQLHA入口
"""

import fcntl
import socket
import time
import sys
from vipha import *
from handler import *
from global_vars.Class_global_vars import *
from config import vars

def main():
    vip_work = vipha()
    work = Worker(vip_work)
    work.vars_init(vars["log_level"], vars) #初始化 参数已经进入 global全局参数
    logger = global_var.get_global_vars("logger")
    sleeptime = global_var.get_global_vars("sleeptime")
    work.check_vars(vars) #做参数检查,检查参数的合法性检查的是vars用户参数
    lock_file = None
    stat_file = None

    ##以下做文件锁避免多次调用启动
    try:
        hostname = socket.gethostname()
        lock_file = global_var.get_global_vars("lock_file")
        lock_file_fd = open(lock_file,"w+",encoding = 'utf-8') #文件锁文件

        #监控文件
        stat_file = global_var.get_global_vars("stat_file")
        stat_file_fd = open(stat_file, "w+", encoding = 'utf-8')
        stat_file_fd.seek(0, 0)
        stat_file_fd.write("1")
        stat_file_fd.flush()

        global_var.set_global_vars("stat_file_fd", stat_file_fd)
    except Exception as e:
        logger.error("lock_file:{} create error.\nexcept:{}" . format(lock_file, e))
        sys.stdout.flush()
        exit(-1)

    try:
        lock_file_fd.write(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
        lock_file_fd.flush()
        fcntl.lockf(lock_file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception as e:
        logger.error("write lock_file:{} fail.\nexcept:{}" . format(lock_file, e))
        sys.stdout.flush()
        exit(-1)

    n = 0
    while 1: ##大循环检查
        #检查stat_file状态，以决定后续VIP是否需要漂移
        #0=>关闭VIP, 1=>维持不变, 2=>启动VIP
        #自动恢复,设定为20*sleeptime秒,一般监控在1分钟内即可触发报警
        #循环检查20次
        if n ==  20: 
            stat_file_fd.seek(0, 0)
            if stat_file_fd.read(1).strip() != '1':
                stat_file_fd.seek(0, 0)
                stat_file_fd.write("1")
                stat_file_fd.flush()
                logger.warning("stat_file reset to '1' atfer 20*sleeptime")
            n = 0

        logger.info("="*30 + "GreatSQLHA stat check loop begin" + '='*30)
        stat = work.check_stat()
        vip_stat = work.check_vip(stat)
        work.set_vip(vip_stat)
        time.sleep(sleeptime)

        #本次检查结果不为1（可能状态发生变化了），则重试检查几次，确认不会发生误判
        stat_file_fd.seek(0, 0)
        if stat_file_fd.read(1).strip() != '1':
            n += 1

    return

##程序开始
if __name__ == '__main__':
    main()
