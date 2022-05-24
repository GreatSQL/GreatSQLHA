import traceback

__all__ = ['global_var']
class global_var:
    """这是全局参数管理类,用于管理全局参数"""
    _my_global = {}
    _all_global = []
    @staticmethod
    def set_global_vars(vars, values):
        """
        set one vars
        :param vars: what global vars will set
        :param values: what values your set
        :return:  no value
        """
        try:
            if isinstance(vars,str) != 1:
                raise TypeError
            global_var._all_global.append(vars)
            global_var._my_global[vars] = values
        except Exception as e:
            traceback.print_exc()
            exit()
    @staticmethod
    def get_global_vars(vars):
        """
        get one para
        :param vars: what global vars will get
        :return:return this para values
        """
        try:
            if isinstance(vars, str) != 1:
                raise TypeError
            return global_var._my_global[vars]
        except KeyError as e:
            traceback.print_exc()
            print("no key in _my_global for {}".format(vars))
            exit()
        except Exception as e:
            traceback.print_exc()
            exit()
    @staticmethod
    def get_all_global_vars():
        """
        return a dict of all paras
        :return: return a dict of all paras
        """
        return global_var._my_global
