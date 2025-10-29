from django.db import models


# Create your models here.
class Users(models.Model):  # 用户
    username = models.CharField(max_length=20)  # 用户名称
    email = models.CharField(max_length=50)  # 邮箱
    password = models.CharField(max_length=20)  # 密码
    group = models.IntegerField()  # 类别（用户，管理员）


class Article(models.Model): # 健康百科文章
    title = models.CharField(max_length=40)  # 文章标题
    author = models.CharField(max_length=40)  # 作者
    paragraph_1 = models.TextField()  # 文章第一段
    paragraph_2 = models.TextField()  # 文章第二段
    image = models.CharField(max_length=100)  #插图


class BasicData(models.Model):  # 药材基础数据
    name = models.TextField()  # 药材名称
    source = models.TextField()  # 源于
    paozhi = models.TextField()   # 炮制方法
    xingzhuang = models.TextField()  # 性状
    xwgj = models.TextField()  # xwgj
    gnzz = models.TextField()  # 功能
    pzzy = models.TextField()  #
    yfyl = models.TextField() # 用法用量
    zc = models.TextField()  # 贮藏方法
    syzy = models.TextField()  # 使用注意
    ckzl = models.TextField()  #


class QSHistory(models.Model): # 问答历史
    qid = models.CharField(max_length=200,default='')  # 历史提问
    question = models.TextField() # 历史提问
    ans = models.TextField()  # 历史回答
    satisfy = models.IntegerField(default=1)  # 是否满意
    user = models.CharField(max_length=20, default='未登录')  # 提问用户
