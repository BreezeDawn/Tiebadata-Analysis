# 使用 sqlalchemy ORM 进行数据表的管理
# 用户和文章是一个一对多的关系,每篇文章有一个外键指向 users 表中的主键 id
import json

from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Text, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# sqlalchemy 的 Declarative 系统能够将我们的数据表结构用 ORM 的语言描述出来
Base = declarative_base()


class User(Base):
    # 表名
    __tablename__ = 'users'

    # 表编码
    __table_args__ = {
        'mysql_charset': 'utf8mb4'
    }

    # 类中的每一个 Column 代表数据库中的一列,在 Colunm中，指定该列的一些配置
    # nullable=False 代表这一列不可以为空，index=True 表示在该列创建索引。
    id = Column(Integer, primary_key=True)
    username = Column(String(64), nullable=False, index=True)  # 用户名
    level = Column(String(64))  # 等级
    avatar_url = Column(String(1024))  # 头像地址
    articles = relationship('Article', backref='author')  # 发表的帖子
    replys = relationship('Reply', backref='user')  # 发表的评论

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.username)


class Article(Base):
    __tablename__ = 'articles'

    __table_args__ = {
        'mysql_charset': 'utf8mb4'
    }

    id = Column(Integer, primary_key=True)
    tid = Column(String(64), nullable=False, index=True)  # Tid
    title = Column(String(255))  # 标题
    reply_num = Column(String(64))  # 带楼中楼的评论量
    create_time = Column(String(64))  # 创建时间
    user_id = Column(Integer, ForeignKey('users.id'))  # 作者

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.title)


# 帖子和评论的多对多关系表
article_reply = Table(
    'article_reply', Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id')),
    Column('reply_id', Integer, ForeignKey('replys.id'))
)


class Reply(Base):
    __tablename__ = 'replys'

    __table_args__ = {
        'mysql_charset': 'utf8mb4'
    }

    id = Column(Integer, primary_key=True)
    tid = Column(String(64), nullable=False, index=True)  # Tid
    content = Column(Text())  # 评论内容
    create_time = Column(String(64))  # 评论时间
    user_id = Column(Integer, ForeignKey('users.id'))  # 评论用户

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.tid)


if __name__ == '__main__':
    db_url = "mysql+pymysql://{u}:{p}@{host}:{port}/{database}"
    # 获取数据库链接构造参数
    f = open("./db.dat")
    db = json.load(f)
    f.close()

    # 创建 sqlalchemy 引擎对象
    engine = create_engine(db_url.format(**db))

    # 使用引擎创建所有表
    Base.metadata.create_all(engine)
