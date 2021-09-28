# python标准库
import json
import re
from sys import path
from PIL.Image import new
from django import contrib
import threading
import os
from bs4 import BeautifulSoup
from django.db.models.signals import pre_migrate
from django.template.defaultfilters import default, title

# 第三方插件库
from blog import models
from django.db.models.aggregates import Count
from blog.models import Category, UserInfo
from django.shortcuts import redirect, render, HttpResponse
from django.contrib import auth    # 超级用户模块
from django.http import JsonResponse, response
from django.db import transaction
from django.db.models.functions import TruncMonth  # 使日期截断至月
from django.db.models import F
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required

# 自建库
from .Myforms import UserForm
from blog.utils.validCode import get_valid_code_img
from cnblog import settings

# ---逻辑内容---


def login(request):

    if request.method == 'POST':
        response = {"user": None, "msg": None}  # 响应字典
        user = request.POST.get("user")
        pwd = request.POST.get("pwd")
        valid_code = request.POST.get("valid_code")

        # 验证验证码
        valid_code_str = request.session.get("valid_code_str")
        if valid_code.upper() == valid_code_str.upper():
            # 用户名密码验证
            user = auth.authenticate(username=user, password=pwd)
            if user:
                auth.login(request, user)  # request.user == 当前登录对象
                response["user"] = user.username
                response["msg"] = "log in success!"
            else:
                response["msg"] = "username or password error!"  # 响应信息
        else:
            response["msg"] = "valid code error!"  # 响应信息
        return JsonResponse(response)  # 返回响应字典

    return render(request, 'login.html')


def get_validCode_img(request):
    '''
    获取验证码图片
    '''

    data = get_valid_code_img(request)

    return HttpResponse(data)


def index(request):

    article_list = models.Article.objects.all().order_by("-nid")

    return render(request, 'index.html', {"article_list": article_list})


def logout(request):

    auth.logout(request)  # request.session.flush()

    return redirect("/index/")


def register(request):
    if request.is_ajax():
        form = UserForm(request.POST)

        response = {"user": None, "msg": None}
        if form.is_valid():
            response["user"] = form.cleaned_data.get("user")

            # 生成一条用户纪录
            user = form.cleaned_data.get("user")
            pwd = form.cleaned_data.get("pwd")
            email = form.cleaned_data.get("email")
            blog_name = request.POST.get("blog_name")
            avatar_obj = request.FILES.get("avatar")

            extra = {}
            # 判断用户有没有上传头像
            if avatar_obj:
                extra["avatar"] = avatar_obj

            # 创建博客
            blog = models.Blog.objects.create(title=blog_name, site_name=user, theme="default.css")
            UserInfo.objects.create_user(
                username=user, password=pwd, email=email, blog=blog, **extra)

        else:
            response["msg"] = form.errors

        return JsonResponse(response)

    form = UserForm()

    return render(request, 'register.html', {"form": form})


def get_classication_data(username):
    '''
    分类信息查询函数，不是视图！！
    '''

    user = UserInfo.objects.filter(username=username).first()
    blog = user.blog
    article_count_dic = models.Article.objects.filter(user=user).aggregate(c=Count("nid"))
    article_count = article_count_dic.get("c")


    return {"user": user, "blog": blog, "article_count": article_count}


def home_site(request, username, **kwargs):
    '''
    个人站点视图
    '''
    # 判断用户是否存在
    user = UserInfo.objects.filter(username=username).first()
    if not user:
        return render(request, '404_notfound.html')
    else:

        # 分类信息查询
        context = get_classication_data(username)

        # 获取当前站点的所有文章
        # 基于对象查询
        # article_list = user.article_set.all()
        # 基于__查询，JOIN查询
        article_list = models.Article.objects.filter(user=user).all()

        # 判断是否是跳转

        if kwargs:
            condition = kwargs.get("condition")
            param = kwargs.get("param")
            blog = models.Blog.objects.filter(site_name=username).first()

            if condition == "category":
                article_list = article_list.filter(category__title=param, category__blog=blog).all()
            elif condition == "tag":
                print(param)
                article_list = article_list.filter(tags__title=param, tags__blog=blog).all()
            elif condition == "archive":
                year, month = param.split("-")
                article_list = article_list.filter(
                    create_time__year=year, create_time__month=month, tags__blog=blog).all()

        # 添加article_list到字典中去
        context["article_list"] = article_list

        return render(request, "home_site.html", context)


def article_detail(request, username, article_number):
    '''
    文章详情页
    '''
    user = UserInfo.objects.filter(username=username).first()
    article = models.Article.objects.filter(
        user=user, nid=article_number).first()
    comments = models.Comment.objects.filter(article=article).all()

    if not (user and article):
        return render(request, '404_notfound.html')
    else:
        context = get_classication_data(username)
        context["article"] = article
        context["comments"] = comments
        return render(request, 'article_detail.html', context)


def digg(request):
    '''
    点赞视图函数
    '''
    is_up = json.loads(request.POST.get("is_up")) # 将字符串的true&false反序列化成布尔值
    article_number = request.POST.get("article_number")
    user_id = request.user.nid                    # 获取当前登录人的id

    response = {"state":True}  # 构建响应字典

    updown_obj = models.ArticleUpDown.objects.filter(article_id = article_number, user_id=user_id).first()

    if not updown_obj:

        ard = models.ArticleUpDown.objects.create(user_id=user_id, article_id=article_number, is_up=is_up)
        if is_up:
            models.Article.objects.filter(nid=article_number).update(up_count=F("up_count")+1)
        else:
            models.Article.objects.filter(nid=article_number).update(down_count=F("down_count")+1)
    else:

        response["state"] = False
        response["handled"] = updown_obj.is_up

    return JsonResponse(response)

def comment(request):
    '''
    评论视图函数(包含邮件发送)
    '''
    response = {}

    if request.is_ajax():
        user = request.user
        content = request.POST.get("content")
        article_number = request.POST.get("article_number")
        parent_comment_id = request.POST.get("parent_comment_id")

        article = models.Article.objects.filter(nid=article_number).first()

        # 事务操作
        with transaction.atomic():
            comment_obj = models.Comment.objects.create(content=content, article_id=article_number, user=user, parent_comment_id=parent_comment_id)
            models.Article.objects.filter(nid=article_number).update(comment_count=F("comment_count")+1)

        response["create_time"] = comment_obj.create_time.strftime("%Y-%m-%d %X")
        response["username"] = request.user.username
        response["content"] = content
        if parent_comment_id:
            parent_comment_obj = comment_obj.parent_comment
            response["parent_comment_user"] = parent_comment_obj.user.username
            response["parent_comment_content"] = parent_comment_obj.content

        # 异步发送邮件

        subject = "您的文章%s新增了一条评论内容，请查看"%article.title
        message = content
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [article.user.email]

        threading.Thread(target=send_mail, args=(
            subject, message, from_email, recipient_list,
        ))

        return JsonResponse(response)

def comment_tree(request):
    '''
    评论树视图函数
    '''
    if request.is_ajax():
        article_number = request.POST.get("article_number")
        comments = list(models.Comment.objects.filter(article_id=article_number).values_list(
            "nid", "user__username", "content", "parent_comment_id" ))
        return JsonResponse(comments, safe=False)

@login_required
def backend(request):
    '''
    后台管理页面
    '''
    username = request.user.username
    context = get_classication_data(username)  # blog user article_count
    articles = models.Article.objects.filter(user = context.get("user").nid).all()
    context['articles'] = articles

    return render(request, 'backend/backend.html', context)

@login_required
def add_article(request):
    '''
    文章添加页面
    '''
    user = request.user
    category_list = models.Category.objects.filter(blog=user.blog).all()
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        category_id = request.POST.get("category_id")
        print(category_id)

        soup = BeautifulSoup(content, "html.parser")
        # 过滤script标签
        for tag in soup.find_all():
            if tag.name == "script":
                tag.decompose()

        # 获取content中的文本为desc
        desc = soup.text[0:150] + "..."

        models.Article.objects.create(title=title, content=str(soup), desc=desc, user=request.user, category_id=category_id)

        path = os.path.join("/",request.user.username,"backend").replace("\\","/")
        return redirect(path)

    return render(request, 'backend/add_article.html', {"category_list": category_list})

@login_required
def del_article(request, article_number):
    '''
    文章删除视图
    '''
    models.Article.objects.filter(user=request.user, nid=article_number).delete()
    path = os.path.join("/",request.user.username,"backend").replace("\\","/")
    return redirect(path)

@login_required
def upd_article(request, article_number):
    '''
    文章删除视图
    '''
    article = models.Article.objects.filter(user=request.user, nid=article_number).first()
    title = article.title
    content = article.content

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        models.Article.objects.filter(user=request.user, nid=article_number).update(title=title,content=content)

        path = os.path.join("/", request.user.username, "articles", article_number).replace("\\", "/")

        return redirect(path)

    return render(request, 'backend/upd_article.html', {"title":title, "content":content})

def upload(request):
    '''
    图片上传视图
    '''
    img = request.FILES.get("upload_img")
    path = os.path.join(settings.MEDIA_ROOT, "add_article_img", img.name)

    with open(path, 'wb') as f:
        for line in img:
            f.write(line)

    response = {
        "error": 0,
        "url": "/media/add_article_img/%s"%img.name,
    }

    return HttpResponse(json.dumps(response))


@login_required
def add_category(request):
    '''
    添加分类视图函数
    '''
    # if request.is_ajax():
    #     user = request.user
    #     blog = user.blog
    #     new_category = request.POST.get("new_category")
    #     my_category = models.Category.objects.create(title=new_category, blog=blog)
    #     response = {}
    #     response["title"] = my_category.title
    #     response["nid"] = my_category.nid

    #     return JsonResponse(response)
    blog = request.user.blog
    categorys = models.Category.objects.filter(blog=blog).all()

    if request.is_ajax():
        new_category = request.POST.get("new_category")
        models.Category.objects.create(title=new_category, blog=blog)

    return render(request, 'backend/add_category.html', {"categorys": categorys})

@login_required
def del_category(request):
    '''
    删除分类的视图函数
    '''
    category_id= request.POST.get("category_id")

    models.Article.objects.filter(category_id=category_id).update(category_id="")

    models.Category.objects.filter(nid=category_id).delete()

    return HttpResponse('ok')