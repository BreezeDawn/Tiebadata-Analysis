# 请求数据
# 提取数据
# 存储数据
# 分析数据
# 分析数据时记得根据楼主时间中'-'的个数判断是否今年
# 人气统计 - 过去一周的 活跃人数(符合日期的评论的用户+符合日期的帖子的作者-去重)/新增帖子(存储的帖子过滤掉不符合日期的帖子)
# 影响力分析 - 过去一周的 最佳帖子-回复数最高的帖子排名(带楼中楼/不带楼中楼)/最佳吧友-平均帖子评论数-不带楼中楼(根据用户外键查找符合日期的帖子,再根据帖子多对多统计评论数,取平均值)
# 活跃度分析 - 过去一周的 发表评论最多(根据用户外键查询符合日期的评论数)/发帖最多(根据用户外键查询符合日期的帖子数)
# 亲密度分析 - 过去一周的 最早回复人(根据用户外键查找所有帖子,多对多查找符合日期的评论,取发表时间最早的,取它的内容和回复时间)/
#                       最频繁回复人(根据用户外键查找所有帖子,多对多查找符合日期的评论,取所有评论的用户,统计次数)

import datetime
import json

import requests

from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Logger
from models import User, Article, Reply

# 创建日志器
logging = Logger('./logging.log', level='debug')


class TiebaData:
    def __init__(self):
        self.url = "http://tieba.baidu.com/f?kw={kw}&ie=utf-8&pn={{}}"
        self.detail_url = 'https://tieba.baidu.com/p/{}?pn={}'
        self.headers = {
            "Referer": "https://tieba.baidu.com",
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36"
        }
        self.a_week_ago_time = self.get_time()
        self.articles_list = []
        self.engine_session = self.get_engine_session()

    def run(self):
        # 输入贴吧名
        kw = input('输入贴吧名:')
        self.url = self.url.format(kw=kw)
        # 获取一周内帖子的id
        self.get_tiezi_id()
        # 存储所有帖子/作者
        self.save()

    def get_tiezi_id(self):
        num = 0
        prev_last = ''
        # 一直请求,一页一页拿取页面数据,直到不满足一周内
        while True:
            # 构造请求链接
            url = self.url.format(num)

            # 获取响应
            response = requests.get(url, headers=self.headers)
            html = response.content.decode()

            # 提取本页所有帖子的模块
            e = etree.HTML(html)
            li_elements = e.xpath("//li[@class='tl_shadow tl_shadow_new']")

            # 判断是否尾页
            now_last = li_elements[-1].xpath(".//div[@class='ti_title']/span/text()")[0] \
                if li_elements[-1].xpath(".//div[@class='ti_title']/span/text()") else '空标题'
            if now_last == prev_last:
                print('不好意思,到头了')
                return
            prev_last = now_last

            for li in li_elements:
                # 如果超过一周立刻停止拿取id
                last_reply_time = li.xpath(".//span[@class='ti_time']/text()")[0]
                print('当前时间%s,可以爬取,正在爬取-----------' % last_reply_time)
                if last_reply_time == self.a_week_ago_time:
                    print('当前时间%s,不可爬取,立即停止' % last_reply_time)
                    print(self.articles_list)
                    return

                    # 只要最后评论时间在一周内就拿它的id/title/reply_num
                tid = li.xpath(".//a[@class='j_common ti_item']/@tid")[0] \
                    if li.xpath(".//a[@class='j_common ti_item']/@tid") else ''
                title = li.xpath(".//div[@class='ti_title']/span/text()")[0] \
                    if li.xpath(".//div[@class='ti_title']/span/text()") else '空标题'
                reply_num = li.xpath('.//span[@class="btn_icon"]/text()')[0]

                self.articles_list.append([tid, title, reply_num])
            # 页数变更
            num += 50

    def save(self):
        for article in self.articles_list:
            tid = article[0]
            title = article[1]
            reply_num = article[2]
            article_id = self.article_data(tid, title, reply_num)
            self.reply_data(article_id, tid)

    def article_data(self, tid, title, reply_num):
        # 构造请求链接
        url = self.detail_url.format(tid, 0)

        # 获取响应
        response = requests.get(url, headers=self.headers)
        html = response.content.decode()

        # 提取楼主模块
        e = etree.HTML(html)
        # 有可能帖子被删除,如果取不到直接return
        try:
            li = e.xpath("//li[@class='list_item post_list_item default_feedback j_post_list_item    no_border']")[0]
        except IndexError:
            logging.logger.error('该帖子取不到楼主模块:Tid-%s' % tid)
            return

        # 提取楼主(作者)数据
        author_name = li.xpath(".//div[@class='list_item_top_name']//span[1]/a/text()")[0]
        author_avatar_url = li.xpath(".//div[@class='list_item_top_avatar']//span/img/@src")[0]
        author_level = li.xpath(".//div[@class='list_item_top_name']//span[2]/text()")[0] if len(
            li.xpath(".//div[@class='list_item_top_name']//span[2]/text()")[0]) <= 2 else '吧务'
        # 存储楼主(作者)数据
        self.save_user_data(author_name, author_avatar_url, author_level)

        # 提取帖子数据
        article_tid = tid
        article_title = title
        article_reply_num = reply_num
        article_create_time = li.xpath(".//div[@class='list_item_top_name']//span[3]/text()")[0]
        if ('-' not in article_create_time) and (':' not in article_create_time):
            article_create_time = li.xpath(".//div[@class='list_item_top_name']//span[4]/text()")[0]
        # 存储帖子数据
        article_id = self.save_article_data(article_tid, article_title, article_create_time, author_name,
                                            article_reply_num)
        return article_id

    def save_user_data(self, username, avatar_url, level):
        # 查询用户是否已存在
        user = self.engine_session.query(User).filter_by(username=username).first()
        if user:
            logging.logger.warning('用户: %s 已存在,不必再次存储' % user.username)
            return

        # 创建用户
        user = User()
        user.username = username
        user.avatar_url = avatar_url
        user.level = level

        # 存储用户
        self.engine_session.add(user)
        try:
            self.engine_session.commit()
        except BaseException as e:
            logging.logger.error('用户: %s 存储失败,失败原因 %s ' % (user.username, e))
            return
        logging.logger.info('用户: %s 存储成功' % user.username)

    def save_article_data(self, tid, title, create_time, user_name, reply_num):
        # 查询文章是否已存在
        article = self.engine_session.query(Article).filter_by(tid=tid).first()
        if article:
            logging.logger.warning('文章: Tid-%s 已存在,不必再次存储' % article.tid)
            return

        # 创建帖子
        article = Article()
        article.tid = tid
        article.title = title
        article.reply_num = reply_num
        article.create_time = create_time
        # 因为存储文章前事先保存了文章的用户,所以直接查询拿取作者id
        user = self.engine_session.query(User).filter_by(username=user_name).first()
        article.user_id = user.id

        # 存储帖子
        self.engine_session.add(article)
        try:
            self.engine_session.commit()
            logging.logger.info('文章: Tid-%s 存储成功' % article.tid)
            return article.id
        except BaseException as e:
            logging.logger.error('文章: Tid-%s 存储失败,失败原因 %s ' % (article.tid, e))
            return

    def reply_data(self, article_id, tid):
        num = 0
        prev_last = ''
        while True:
            # 构造请求链接
            url = self.detail_url.format(tid, num)

            # 获取响应
            response = requests.get(url, headers=self.headers)
            html = response.content.decode()

            # 提取本页所有评论的模块
            e = etree.HTML(html)
            li_elements = e.xpath("//li[@class='list_item post_list_item default_feedback j_post_list_item    ']")
            if not li_elements:
                logging.logger.warning('该帖没有评论,真惨')
                return

            # 判断是否尾页
            now_last = li_elements[-1].xpath("./@tid")[0]
            if now_last == prev_last:
                print('不好意思,到头了')
                return
            prev_last = now_last

            # 提取数据
            for li in li_elements:
                # 提取评论用户数据
                user_name = li.xpath(".//div[@class='list_item_top_name']/span[1]/a/text()")[0]
                user_level = li.xpath(".//div[@class='list_item_top_name']/span[2]/text()")[0] if li.xpath(
                    ".//div[@class='list_item_top_name']/span[2]/text()") else '吧务'
                user_avatar_url = li.xpath(".//img[@alt='头像']/@src")[0]
                # 存储用户
                self.save_user_data(user_name, user_avatar_url, user_level)

                # 提取评论数据
                reply_tid = li.xpath("./@tid")
                reply_create_time = li.xpath(".//div[@class='list_item_top_name']/span[3]/text()")[0]
                reply_content = li.xpath(".//div[@lz='0']/text() | .//div[@lz='1']/text()")[0].replace(
                    '                ', ' ')
                if reply_content == ' ':
                    reply_content = '这是一个纯表情或者图片评论导致无法获取,可是有点水哦~'
                # 存储评论
                self.save_reply_data(article_id, reply_tid, reply_create_time, reply_content, user_name)

            # 页数变更
            num += 30

    def save_reply_data(self, article_id, reply_tid, create_time, content, username):
        # 查询评论是否已存在
        reply = self.engine_session.query(Reply).filter_by(tid=reply_tid).first()
        if reply:
            logging.logger.warning('评论: Tid-%s 已存在,不必再次存储' % reply.tid)
            return

        # 创建评论
        reply = Reply()
        reply.tid = reply_tid
        reply.content = content
        reply.create_time = create_time
        # 因为存储评论前事先保存了评论的用户,所以直接查询拿取评论id
        user = self.engine_session.query(User).filter_by(username=username).first()
        reply.user_id = user.id
        reply.article_id = article_id

        # 存储评论
        self.engine_session.add(reply)
        try:
            self.engine_session.commit()
        except BaseException as e:
            logging.logger.error('评论: Tid-%s 存储失败,失败原因 %s ' % (reply.tid, e))
            return
        logging.logger.info('评论: Tid-%s 存储成功' % reply.tid)

    @staticmethod
    def get_time():
        aweekago = datetime.datetime.today() - datetime.timedelta(weeks=1)
        mounth = aweekago.month
        day = aweekago.day - 1  # 遇到一周前的前一天就停止,所以要减1
        return str(mounth) + '-' + str(day)

    @staticmethod
    def get_engine_session():
        db_url = "mysql+pymysql://{u}:{p}@{host}:{port}/{database}"

        # 获取数据库链接构造参数
        f = open("./db.dat")
        db = json.load(f)
        f.close()

        engine = create_engine(db_url.format(**db))
        engine_session = sessionmaker(bind=engine, autocommit=False)
        return engine_session()


class TiebaAnalysis:
    pass


if __name__ == '__main__':
    tieba = TiebaData()
    tieba.run()
