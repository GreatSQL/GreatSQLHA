###配置参数
# vip => 高可用虚拟IP
# mgr_seeds => MGR各节点的IP+对应绑定的网卡（务必填写IP地址格式，不能填写主机名）
# gateway => 网关IP地址，用于检测绑定VIP后是否能ping通网关
# mysql_port => MySQL运行端口，用于检测连通性
# mgr_port => MGR服务运行的端口
# user,passwd => 连接MySQL的账号密码
# sleeptime => 代表循环检测时间，单位为秒
# logdir => 程序日志目录
# log_level => 记录log等级，可选值有 DEBUG|INFO|WARNING|ERROR|CRITICAL

vars = {"vip":"172.16.130.200", \
        "mgr_seeds":{"172.16.130.197":"ens3","172.16.130.198":"ens3","172.16.130.199":"ens3"}, \
        "gateway":"172.16.130.1", \
        "mysql_port":"3306", \
        "mgr_port":"33061", \
        "user":"yejr", \
        "passwd":"yejr", \
        "sleeptime":3, \
        "logdir":"/tmp/", \
        "lock_file": "/tmp/GreatSQLHA.lock", \
        "stat_file": "/tmp/GreatSQLHA.stat", \
        "log_level":"INFO"}
