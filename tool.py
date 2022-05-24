"""
各种辅助和实现函数
"""
import socket
import pymysql.cursors
import psutil
import subprocess


# 定义几个关键函数名
__all__ = ['connect_mysqld', \
        'check_localip_in_mgr', \
        'check_mgr_primary', \
        'gateway_connectable', \
        'check_vip_local_bound', \
        'ip_connectable', \
        'unbind_vip', \
        'bind_vip']

# IP地址（全局变量名，避免多次获取）
ipaddr = None 
# 网关（全局变量名，避免多次获取）
g_gateway = None

def get_netcard_by_ip(logger, ipaddr, local_ip):
    """
    返回指定本地IP的网卡名
    - param: ipaddr => get_ipaddr_info() 返回的信息例如[('192.168.99.101':'eth0'),]
    - return:
        1 => 异常
        正常网卡名称
    """
    logger.debug("get_netcard_by_ip: ipaddr:{}" . format(ipaddr))
    for i in ipaddr:
        if i[0] == local_ip:
            return i[1]
    return 1

def  ip_connectable(logger, ip):
    """
    检查指定的VIP是否能ping通
    - param: logger，日志系统
    - param: ip，待检查的IP地址
    - return:
        0 能ping通
        1 不能ping通
    """
    res = subprocess.getstatusoutput('/bin/ping -c 3 ' +ip)
    logger.info("ip_connectable: ping reslut is {}" . format(res))

    if  '0 received' in res[1]:
        logger.warning("ip_connectable: {} ping timeout" . format(ip))
        return 1
    else:
        return 0

def get_mysql_errno(e):
    """
    返回连接mysqld报错的错误码
    - param e:异常抛出
    - return: 错误码数字
    """
    l = list("{}" . format(e))
    s = ''
    for i in range(1,5):
        s = s + l[i]

    return int(s)

def get_ipaddr_info(info):
    """
    根据psutil.net_if_addrs()输入的IP地址，返回[IP+网卡]信息
    - param info: psutil.net_if_addrs()获取到的IP地址
    - return: 返回一个全部IP地址和网卡的列表 [('eth0':'192.168.99.101')]
    """
    netcard_info = []
    for k, v in info.items():
        for item in v:
            if item[0] == 2 and not item[1] == '127.0.0.1':
                netcard_info.append((item[1], k))
    return netcard_info

def check_port_alived(logger, ip, port):
    """
    检查端口是否存活
    - param logger:日志系统
    - param ip: 检测服务器的IP
    - param port: 检测服务的端口
    - return:
        0 => 正常
        1 => 异常
    """
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        if isinstance(ip, str) != 1 or isinstance(port, str) != 1:
            logger.error("check_port_alived:ip:port {}:{} type not [str]..." . format(ip, port), exc_info = True)
            exit(-1)

        s.connect((ip, int(port)))
        s.shutdown(2)
        s.close()
        logger.info("check_port_alived:ip:port {}:{} alived!" . format(ip,port))
        return 0
    except Exception as e:
        logger.error("check_port_alived:{}".format(e), exc_info = True)
        return 1

##[STAGE1 检查函数]
def check_localip_in_mgr(logger, mgr_seeds):
    """
    检查本地IP地址是否在MGR列表中，如果没有在集群列表中则返回1，需要比较IP地址和网卡名称两个方面
    - param logger: 日志系统
    - param mgr_seeds: 集群IP地址列表和网卡字典
    - return:
        1 => 异常
        成功则返回匹配的本地地址
    """
    if isinstance(mgr_seeds, dict) != 1:
        logger.error("check_localip_in_mgr: {} type not [dict]".format(mgr_seeds), exc_info=True)
        exit(-1)

    #获取全部的网卡信息
    info = psutil.net_if_addrs()

    #声明为全局变量
    global  ipaddr

    #获得网卡信息形如 [('192.168.99.101':'eth0')]
    ipaddr = get_ipaddr_info(info)

    #输出所有IP地址
    logger.info("check_localip_in_mgr: local ip:{}" . format(ipaddr))
    for i in ipaddr:
        #如果这个网卡信息在mgr_seeds字典中，则输出到日志
        if  i in (list(mgr_seeds.items())):
            logger.info("check_localip_in_mgr: local ip:{} in mgr_seeds" . format(i[0]))

            #并且返回这个IP信息 i[0]是IP信息 i[1]是网卡名
            return i[0]

    #否则找不到这个网卡信息
    logger.info("check_localip_in_mgr: local ip {} not in mgr_seeds" . format(ipaddr))

    #返回1表示在mgr_seeds参数中不包含这个ip地址和网卡
    return 1

##[STAGE2 检查函数]
def connect_mysqld(logger, *vars):
    """
    检查是否能够连接上mysql服务器进程，当前判断两个地方
        1. 端口是否可用
        2. mysql是否可连接并执行一个简单查询

    - param logger:日志系统
    - param *vars: ip, port, user, passwd几个选项序列指针
    - return:
        0 => 正常
        1 => 异常
    """
    #check_port_alived用于判断端口是否可用 check_mysqld_alived用于判断mysqld是否可以连接
    #if check_port_alived(logger,vars[0],vars[1]) == 0 and check_mysqld_alived(logger,*vars) == 0:
    if check_mysqld_alived(logger, *vars) == 0:
        return 0
    else:
        return 1

def check_mysqld_alived(logger, *vars):
    """
    检查mysqld进程是否已启动，如果没有启动mysqld则其他检查也都没必要了
    - param *vars: ip, port, user, passwd几个选项序列指针
    - return:
        0 => 关闭
        1 => 启动
    """
    if len(vars) != 4:
        logger.error("check_mysqld_alived: in vars error", exc_info=True)
        exit(-1)

    """
    # 忽略检查，在check_vars()已检查过
    for i in vars:
        if isinstance(i,str) != 1:
            logger.error("check_mysqld_alived:str req but type is".format(type(i)), exc_info=True)
            exit(-1)
    """

    # 测试连接
    try:
        db = pymysql.connect(host=vars[0], port=int(vars[1]), user=vars[2], password=vars[3])
        logger.info("check_mysqld_alived: mysqld connect succ!")
        cur = db.cursor()
        # 执行一个测试，因为有可能当前负载非常高，无法响应
        try:
            cur.execute("select benchmark(10000, 1+1);")
            cur.fetchall()
        except Exception as e:
            logger.warning("check_mysqld_alived: mysqld connect succ, but benchmark() query failed...")
            return 0
        db.close()
        return 0
    except Exception as e:
        #如果只是密码错误则说明mysqld可以连接，错误码为1045
        if get_mysql_errno(e) == 1045:
            logger.info("check_mysqld_alived: mysqld connect succ, but password error...")
            return 0
        else:
            logger.error("check_mysqld_alived:{}".format(e), exc_info=True)
            return 1

##[STAGE3 检查函数]
def check_mgr_primary(logger, ip, mgr_port, port, user, passwd):
    """
    检查MGR内部端口是否启动来检查MGR已经启动，然后判断本地节点是否为online状态并且在视图中，然后判断本节点是否是主节点
    - param logger: 日志系统
    - param ip: 本地ip
    - param mgr_port: MGR paxos通信内部端口
    - param port: 本地mysqld端口
    - param user: 本地连接用户
    - param passwd: 用户名
    - return:
        0 => MGR内部端口存在且为主
        1 => MGR内部端口不存在或者不为主
    """

    # master 节点查询结果
    mgr_host_list = [[None]]
    # 查看本地是否在集群中且状态为online
    online_stat =  [[None]]


    # 查询本地节点是否为Primary Node（不是主节点显然不应该启动VIP）
    host_list_sql = """SELECT MEMBER_HOST MASTER_NODE FROM
                     performance_schema.replication_group_members WHERE MEMBER_ID IN
                    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE \
                            VARIABLE_NAME = 'group_replication_primary_member');
          """
    # 查询本节点是否在集群中，并且状态为ONLIE（对于recovering以及其他状态的显然不能启动VIP）
    online_stat_sql = """SELECT COUNT(*) FROM performance_schema.replication_group_members WHERE \
            MEMBER_HOST = '""" + socket.gethostbyname(socket.gethostname()) + """' AND \
            MEMBER_STATE = 'ONLINE';"""

    # 查询Primary Node及其状态是否为ONLINE
    try:
        db = pymysql.Connect(host=ip, port=int(port), user=user, passwd=passwd, db="performance_schema")
        cur = db.cursor()

        # 获取Primary Node
        cur.execute(host_list_sql)
        mgr_host_list = cur.fetchall()

        # 确认本地在集群中，且状态为online
        # online_stat = 1，表示状态正常
        # 必须=1 因为要么有结果count(*) = 1要么没结果
        # count(*) = 0 都应该是一行
        cur.execute(online_stat_sql)
        online_stat = cur.fetchall()
        db.close()
    except Exception as e:
        logger.error("check_mgr_primary: {}" . format(e), exc_info=True)
        # 任何数据库的错误应该是退出，如果返回return 1 那么可能造成VIP异常关闭
        exit(-1)

        #return 1  # 数据库异常不做任何判断
        #这里2次跑数据 压力大？断开？
        # 依赖VIP操作的2次检查否则可能出现异常关闭VIP的情况

    try:
        assert len(mgr_host_list) < 2 #断言只有1行或者0行，只有一个Primary Node或结果为空
        assert len(online_stat ) == 1 #断言只有1行，只有一个Online节点
    except Exception as e:
        logger.error("check_mgr_primary: {}" . format(e), exc_info=True)
        # 断言失败应该退出
        exit(-1)

    # 报错 IndexError: tuple index out of range
    # 没有数据返回的时候
    try:
        # 如果结果返回为空值()
        if not(mgr_host_list):
            hostname = None
            logger.error("check_mgr_primary: no data found {}" . format(e), exc_info=True)
        else:
            #第一个0代表第一行 第二个0代表是第一行的第一个字段 二维数组
            hostname = mgr_host_list[0][0]
    except Exception as e:
        logger.error("check_mgr_primary: get mgr host error {}" . format(e), exc_info=True)
        hostname = None

    # 判断本地状态为online，否则返回1
    if online_stat [0][0] != 1:
        logger.error("check_mgr_primary: node:{} not ONLINE or not in replication_group_members view" . \
                format(socket.gethostbyname(socket.gethostname())))
        return 1

    logger.info("check_mgr_primary: node:{} ONLINE" . format(socket.gethostname()))

    # 如果获取的主机名字和获取的主机名不一致，那么认为本地节点不是Primary Node
    if socket.gethostbyname(socket.gethostname()) != hostname:
        logger.info("check_mgr_primary: node:{} not Primary, Primary node is:{}" . \
                format(socket.gethostbyname(socket.gethostname()), hostname))
        return 1

    #否则 说明paxos inter端口可通并且是主
    logger.info("check_mgr_primary: node:{} is MGR Primary" . format(socket.gethostbyname(socket.gethostname())))
    return 0

##[STAGE4 检查函数]
def  gateway_connectable(logger, gateway):
    """
    检查网关是否可连通
    - param logger: 日志系统
    - param gateway: 网关
    - return:
        0 能够ping通
        1 不能ping通
    """
    global g_gateway
    g_gateway = gateway
    return ip_connectable(logger, gateway)

##[STAGE5]
def check_vip_local_bound(logger, vip):
    """
    这个函数用于确认VIP是否在本地
    :param vip:参数设置中的VIP值
    :return: 0 vip在本地 1 vip不在本地
    """

    # 已经在函数 check_localip_in_mgr 中获取过了
    global ipaddr

    for i in ipaddr:
        # 如果vip和其中一个网卡IP相等说明已绑定
        if  vip == i[0]:
            logger.info("check_vip_local_bound: vip:{} had been bound" . format(vip))
            return 0

    # 未绑定到本地
    logger.info("check_vip_local_bound: vip:{} not bound" . format(vip))
    return 1

##[STAGE6]
def unbind_vip(logger, vip, local_ip):
    """
    解绑VIP
    - param logger:日志系统
    - param vip: 虚拟IP
    - param local_ip: 绑定虚拟IP的本地IP
    - return:
        0 解绑成功
        1 解绑失败
    """
    global ipaddr
    global g_gateway
    netcard = get_netcard_by_ip(logger, ipaddr, local_ip)

    unbind_vip_cmd=('/usr/sbin/ip a del ' +vip+ ' dev ' +netcard)
    res = subprocess.getstatusoutput(unbind_vip_cmd)

    # 解绑失败
    if res[0] != 0:
        logger.warning("unbind_vip: '" +unbind_vip_cmd+ "' failed...{}" . format(res), exc_info=True)
        return 1

    # 解绑成功
    logger.info("unbind_vip: " +unbind_vip_cmd+ " succ!" . format(vip))

    return 0


def bind_vip(logger, vip, local_ip):
    """
    绑定VIP
     - param logger: 日志系统
     - param vip: 虚拟IP
     - param local_ip: 绑定虚拟IP的本地IP
     - return:
        0 绑定成功
        1 绑定失败
    """
    global ipaddr
    global g_gateway
    netcard = get_netcard_by_ip(logger, ipaddr, local_ip)

    bind_vip_cmd=('/usr/sbin/ip a add ' +vip+ ' dev ' +netcard)
    res = subprocess.getstatusoutput(bind_vip_cmd)
    
    # 绑定失败
    if res[0] != 0:
        logger.warning("bind_vip: '" +bind_vip_cmd+ "' failed... {}" . format(res), exc_info=True)
        return 1 #执行ifconfig失败

    # 绑定成功，再ping网关，广播VIP和ARP
    res = subprocess.getstatusoutput("/sbin/arping -I " +netcard+ " -c 3 -s " +vip+ " " + g_gateway)

    logger.info("bind_vip: arping {}" . format(res))
    logger.info("bind_vip: '" +bind_vip_cmd+ "' succ!" . format(vip, netcard))

    return 0 #正常标示
