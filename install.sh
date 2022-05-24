#!/bin/bash
#
# 安装GreatSQLHA
#

. ~/.bash_profile
alias cp=cp

conf_basedir="/data/GreatSQLHA"

echo "欢迎使用GreatSQLHA，即将开始安装"

# 准备开始安装，判断&创建安装目录
read -p "请输入安装的目标目录（默认：${conf_basedir}）：" installdir
if [ -z "${installdir}" ] ; then
    installdir=${conf_basedir}
    echo "将安装到 ${installdir}"
fi

if [ ! -d ${installdir} ] ; then
    typeset -u tobe_mkdir
    read -p "安装目录："${installdir}"不存在，是否直接创建：Y/N(Y)" tobe_mkdir

    if [ -z "${tobe_mkdir}" ] ; then
	tobe_mkdir="Y"
    fi

    if [ ${tobe_mkdir} != "Y" ] ; then
    	echo "您选择不创建目录，退出安装！"
    	exit
    else
	mkdir -p ${installdir}
    fi

elif [ `du ${installdir}|tail -n 1|awk '{print $1}'` -gt 0 ] ; then
    typeset -u force_install
    read -p "安装目录 ${installdir} 目录不为空，确定要强行安装吗？Y/N(N)" force_install

    if [ -z "${force_install}" ] ; then
	force_install="N"
    fi

    if [ ${force_install} != "Y" ] ; then
    	echo "不强行安装，退出！"
    	exit
    fi
fi

# 检查是否已安装Python3，以及相应的模块
if [ ! -z "`which python3 | grep 'which.*no.*python3'`" ] ; then
    echo "尚未安装Python3，请自行安装"
    exit
else
    if [ ! -z "`which pip3 | grep 'which.*no.*pip3'`" ] ; then
	echo "尚未安装pip3，请自行安装"
	exit
    else
    	if [ `pip3 list | egrep -i 'PyMySQL|psutil'|wc -l` -lt 2 ] ; then
    	    echo "请先安装psutil,PyMySQL这两个Python模块"
    	    echo "如果连接MySQL的用户采用caching_sha2_password加密算法，还需安装cryptography模块"
    	    exit
	fi
    fi
fi

# 开始安装
typeset -u confirm_config
read -p "请确认config.py中的配置参数都已经修改正确：Y/N(Y)" confirm_config
if [ -z "${confirm_config}" ] ; then
    confirm_config="Y"
fi

if [ "${confirm_config}" != "Y" ] ; then
    echo "请先修改config.py中的配置参数，先退出安装"
    exit
fi

## 获取 config.py 中的logdir
logdir=`grep '"logdir"' config.py | sed 's/.*:"\(.*\)",.*/\1/ig'`

## 获取 python3 路径
python3_path=`which python3|tail -n 1`

## 替换greatsqlha.logrotate  greatsqlha.service中的文件、目录名
sed -i "s#PYTHON_PATH#${python3_path}#ig;s#GreatSQLHA_INSTALL_PATH#${installdir}#ig" greatsqlha.service
sed -i "s#GreatSQLHA_LOG_PATH#${logdir}#ig" greatsqlha.logrotate

# 提醒MySQL账户授权
mysql_user=`grep '"user"' config.py | sed 's/.*:"\(.*\)",.*/\1/ig'`
typeset -u confirm_mysql_grant
read -p "请确认已创建新用户 \"${mysql_user}\"：Y/N(N)" confirm_mysql_grant
if [ -z "${confirm_mysql_grant}" ] ; then
    confirm_config="Y"
fi

if [ "${confirm_mysql_grant}" != "Y" ] ; then
    echo "请先创建MySQL连接用户并授权，先退出安装"
    exit
fi

# 确保各个程序文件都可执行
chmod +x greatsqlha.logrotate greatsqlha.service

cp -f greatsqlha.service /lib/systemd/system/
cp -f greatsqlha.logrotate /etc/logrotate.d/greatsqlha

# 程序文件cp到目标目录
cp -rfp *.py global_vars logger my_exception ${installdir}

# 重新加载systemd，并启动GreatSQLHA
echo "加入greatsqlha服务，重新加载systemd，也可手动执行：systemctl daemon-reload"
systemctl daemon-reload
echo "启动greatsqlha服务，也可手动执行：systemctl start greatsqlha"
systemctl start greatsqlha
