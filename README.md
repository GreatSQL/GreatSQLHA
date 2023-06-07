# GreatSQLHA

[toc]

**提醒**：GreatSQL 8.0.32-24版本开始支持在MGR的读写节点上绑定动态VIP以实现高可用，推荐升级到该版本，详情请参考：[GreatSQL中MGR支持内置vip特性](https://gitee.com/GreatSQL/GreatSQL-Doc/blob/master/relnotes/greatsql-803224/mgr-vip.md)。

## 0. 简介
MGR集群高可用方案，基于VIP漂移机制。

适用于Python 3.6环境，已在CentOS 7.x/8.x + Python 3.6环境下验证通过。

支持 GreatSQL 5.7 & 8.0，同样也支持 MySQL 以及 Percona Server相应版本。

本项目fork自八怪的[HAIPMGR](https://github.com/gaopengcarl/HAIPMGR)。

## 1. 运行环境要求
1. 安装Python 3.6
```
$ yum install -y python3 python3-pip
```
2. 安装psutil>=5.4.3 和 PyMySQL>=1.0.2 模块
```
$ pip3 install --user psutil==5.4.3 PyMySQL==1.0.2
```
3. 如果连接mysql的账户采用 caching_sha2_password 加密方式，则还需要安装 cryptography>=36.0.1 模块。如果还是采用 mysql_native_password 则无需安装此模块。
```
$ pip3 install --user cryptography>=36.0.1
```

## 2. 运行前修改配置
修改配置文件 `config.py` 里的相关参数，例如：
```
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
```
上述参数的作用分别是：
- vip => 高可用绑定的VIP地址
- mgr_seeds => MGR各节点的IP+对应绑定的网卡（务必填写IP地址格式，不能填写主机名）
- gateway => 网关IP地址，用于检测绑定VIP后是否能ping通网关
- mysql_port => MySQL运行端口，用于检测连通性
- mgr_port => MGR服务运行的端口
- user,passwd => 连接MySQL的账号密码
- sleeptime => 代表循环检测时间，单位为秒
- logdir => 程序日志目录
- log_level => 记录log等级，可选值有 DEBUG|INFO|WARNING|ERROR|CRITICAL

**提醒**
上面配置的连接MySQL的账号、密码要先自行测试，并且要提前授权，至少要能连接以及对performance_schema & sys的只读权限，可参考下面的做法：
```
mysql> create user yejr identified by 'yejr';
mysql> grant select on performance_schema.* to yejr;
mysql> grant select on sys.* to yejr;
```

此外，还需要提前设置好正确的hostname、ip信息，例如：
```
# 设置hostname
$ hostnamectl set-hostname mgr1

# 读取hostname
$ hostname
mgr1
```
因为程序运行时需要通过hostname获取ip地址，可以尝试运行下面的小程序确认设置是否正确：
```
# 运行python3
$ python3
Python 3.6.8 (default, Sep 10 2021, 09:13:53)
[GCC 8.5.0 20210514 (Red Hat 8.5.0-3)] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import socket
>>> print(socket.gethostbyname(socket.gethostname()))
172.16.130.197
>>>
```
这样就表示可以了，如果不能获取到正确的ip地址，请检查是否已正确设置了。

## 3. 安装和启动程序
```
# 1. 假定将程序安装到 /data/GreatSQLHA 目录下
# 假定程序包放在 /root/GreatSQLHA 目录下
$ cd /root/GreatSQLHA
$ ls
config.py  global_vars  handler.py  logger  GreatSQLHA.py  my_exception  __pycache__  README.md  TODO.txt  tool.py  vipha.py
# 2. 参考上面说明修改配置文件 config.py

# 3. 执行安装程序install.sh（在各个节点都要安装一遍）
# 根据输出提醒进行安装即可
# 安装完毕后，会自行加入systemd中并启动服务
$ ./install.sh
$ ps -ef | grep GreatSQLHA
root       22056       1  0 16:43 ?        00:00:01 /usr/bin/python3 /data/GreatSQLHA/GreatSQLHA.py
```

如果启动没报错，则 /tmp/GreatSQLHA.log 文件中会记录详细运行结果输出信息，例如：
```
INFO - Longger System Create Finish
INFO - vars_init: All options [INIT] complete!! is:
INFO - options log_level values is INFO
INFO - options logger values is <Logger GreatSQLHA (INFO)>
INFO - options vip values is 172.16.130.200
INFO - options mgr_seeds values is {'172.16.130.197': 'ens3', '172.16.130.198': 'ens3', '172.16.130.199': 'ens3'}
INFO - options gateway values is 172.16.130.1
INFO - options mysql_port values is 3306
INFO - options mgr_port values is 33061
INFO - options user values is yejr
INFO - options sleeptime values is 3
INFO - options logdir values is /tmp/
INFO - options lock_file values is /tmp/GreatSQLHA.lock
INFO - options stat_file values is /tmp/GreatSQLHA.stat
INFO - ==============================GreatSQLHA stat check loop begin==============================
INFO - check_localip_in_mgr: local ip:[('172.16.130.198', 'ens3')]
INFO - check_localip_in_mgr: local ip:172.16.130.198 in mgr_seeds
INFO - check_stat:[STAGE1] local_ip:172.16.130.198 check succ!
INFO - check_mysqld_alived: mysqld connect succ!
INFO - check_stat:[STAGE2] mysqld 172.16.130.198:3306 connect scuess!
INFO - check_mgr_primary: node:wldb3 ONLINE
INFO - check_mgr_primary: node:172.16.130.198 not Primary, Primary node is:172.16.130.197
INFO - check_stat:[STAGE3] 172.16.130.198 not mgr primary...
INFO - check_vip_local_bound: vip:172.16.130.200 not bound
INFO - check_vip: vip should not be bound...
INFO - check_vip:vip 172.16.130.200 not on this node, do nothing
INFO - set_vip: do nothing
...
```
一般而言，INFO级别的日志不用处理，只有WARNING级别以上的日志才需要关注。

运行过程中会生成几个文件：
- /tmp/GreatSQLHA.lock，文件锁，【请不要】手动更改本文件
- /tmp/GreatSQLHA.log，运行日志文件
- /tmp/GreatSQLHA.stat，状态文件，用于监控是否发生了VIP切换，【请不要】手动更改本文件。文件内容不同值分别表示：
    - 0 关闭GreatSQLHA
    - 2 为启动GreatSQLHA，且将会在20*sleeptime后重置为1

## 4. 关闭程序
直接 ctrl+c 终止程序，或直接kill进程ID即可。
若当前节点是Primary Node，关闭或启动程序都不会导致现有VIP切换。


## 5. 程序限制
本程序有以下几项限制条件：
- 只能用于Linux环境下，已在CentOS 7.x/8.x环境中验证通过，其他Linux发行版请自行测试验证。
- 要求MGR运行再单主模式下（group_replication_single_primary_mode=ON）。
- 要求每个服务器上运行MGR单实例的场景，且各节点的MySQL和MGR Paxos通信端口都一样。
- 要求每个MGR实例上都要设置report-host，并且以IP地址的方式上报，例如：report-host=172.16.130.197，因为在逻辑判断中采用IP地址方式。


## 6. 高可用VIP切换与否逻辑过程

在MGR单主模式下，各个判断逻辑如下:
### 阶段1[stage1]
通过初始化参数cluser_ip中的配置判断本节点是否在集群中

### 阶段2[stage2]
检查是否能够连接上MYSQLD服务器进程，主要检查mysqld(已经取消端口检测)可以连接(密码错误算可以连接)

### 阶段3[stage3]
判断内部通信端口是否启动，检查本机是否在MGR中且为online，检查本节点是否是MGR的主节点

### 阶段4[stage4]
通过检查网关的方式,来避免网络隔离出现2个主节点启动两个VIP的情况

经过上面四个阶段的逻辑判断后，将会返回：
- 0，表示状态检查通过，需要开启VIP
- 1，表示状态检查未通过，需要关闭VIP

### 阶段5[stage5]
根据上面四个阶段的返回值来判断是否启动和关闭VIP，于是又有如下几个判断

- 如果需要启动
    - 虚拟VIP是否在本地
        - 如果在本地
            - 则维持现状return 1
        - 如果不在本地
            - 如果还能ping通VIP则本次循环维持现状,等待下次循环检测 return 1
            - 如果不能ping通VIP则做2次检查将阶段1到4再次检查一遍
                - 如果检查失败 return1 维持现状
                - 如果检查成功 return2 启动VIP
- 如果需要关闭
    - 虚拟VIP是否在本地关闭
        - 如果在本地
            - 做二次检查阶段1到4再次检查一遍
                - 如果检查失败 return1 维持现状
                - 如果检查成功 return0 关闭VIP
        - 如果不在本地
            - 维持现状 return0

处理完毕后，本阶段将返：
- 0 关闭VIP
- 1 维持现状不启动也不关闭vip
- 2 启动VIP

### 阶段6[stage6]
根据阶段5的返回值做出相应的VIP各种处理（启动、关闭、保持不变）。

## 7. 高可用切换测试
正式上线前，可以分别模拟下面几种情况，测试GreatSQLHA高可用切换是否能正常工作：
- 1. 关闭服务器
- 2. 关闭数据库
- 3. 关闭MGR
- 4. 连接账号授权不足或密码错误（可能会导致 check_mgr_primary() 函数执行失败而退出程序）
- 5. MySQL负载太高导致状态检查超时失败
- 6. 网卡意外宕机
- 7. 主节点发生网络分区
