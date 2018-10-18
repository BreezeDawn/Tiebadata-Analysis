# 日志配置
import logging
from logging import handlers


class Logger(object):
    # 日志级别关系映射
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }

    def __init__(self, filename, level='info', when='midnight', backCount=3):
        # 定义日志器
        self.logger = logging.getLogger(filename)

        # 设置日志级别
        self.logger.setLevel(self.level_relations.get(level))

        # 定义日志格式
        sh_format = logging.Formatter(
            '%(asctime)s - [line:%(lineno)d] - %(levelname)s: %(message)s'
        )
        th_format = logging.Formatter(
            '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
        )

        # 屏幕输出处理器
        sh = logging.StreamHandler()

        # 指定间隔时间自动生成文件的处理器
        # interval-时间间隔  backupCount-备份文件的个数,如果超过这个个数则自动删除
        # when-间隔的时间单位 S-秒 M-分 H-小时 D-天 W-每星期(interval==0 代表星期一) midnight-每天凌晨
        th = handlers.TimedRotatingFileHandler(filename=filename, when=when, backupCount=backCount,
                                               encoding='utf-8')

        # 给处理器指定输出格式
        sh.setFormatter(sh_format)
        th.setFormatter(th_format)

        # 加入处理器
        self.logger.addHandler(sh)
        self.logger.addHandler(th)


if __name__ == '__main__':
    log = Logger('./all.logs', level='debug')
    log.logger.debug('debug')
    log.logger.info('info')
    log.logger.warning('警告')
    log.logger.error('报错')
    log.logger.critical('严重')
