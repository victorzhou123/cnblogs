# python标准库
import json
import re
from sys import path
from PIL.Image import merge, new
from django import contrib
import threading
import os
from bs4 import BeautifulSoup
from django.db.models.signals import pre_migrate
from django.template.defaultfilters import default, title
from blog import models


# 第三方插件库
from django.db.models.aggregates import Count
from django.shortcuts import redirect, render, HttpResponse
from django.contrib import auth    # 超级用户模块
from django.http import JsonResponse, request, response
from django.db import transaction
from django.db.models.functions import TruncMonth  # 使日期截断至月
from django.db.models import F
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage
from django.contrib.auth.decorators import login_required

# 自建库
from .Myforms import UserForm
from blog.utils.validCode import get_valid_code_img
from cnblog import settings

# ---逻辑内容---


def login(request):
    request.session["kkk"] = "chenggong"

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


def pageinator_bar(request, article_list, article_inside):
    '''
    分页器模块，不是视图
    '''
    try:
        paginator_bar = Paginator(article_list, article_inside)   # paginator对象
        page = int(request.GET.get("page", 1))   # 前端请求的page（号码）
    except EmptyPage as e:
        page = 1

    current_page = paginator_bar.page(page)      # 第page页的数据对象
    count = paginator_bar.count                  # 数据总数
    num_page = paginator_bar.num_pages           # 总页数
    page_range = paginator_bar.page_range        # 页码的列表

    # 保证活跃页面选项居中
    if page < 6:
        page_range = range(1, num_page+1)
    elif page > num_page-5:
        page_range = range(num_page-9,num_page+1)
    else:
        page_range = range(page-4, page+5)

    context = {"article_list": article_list, "page": page, "current_page": current_page, "count": count, "number_page": num_page, "page_range": page_range}

    return context


def index(request):

    article_list = models.Article.objects.all().order_by("-nid")
    context = pageinator_bar(request, article_list, 6)       # context是个字典

    article_hotreading = article_list.order_by("-pageview__pageview_count")[:10] # 热门阅读
    article_hotdiscuss = article_list.order_by("-comment_count")[:10] # 热门阅读
    context["article_hotreading"] = article_hotreading
    context["article_hotdiscuss"] = article_hotdiscuss

    return render(request, 'index.html', context)


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
            models.UserInfo.objects.create_user(
                username=user, password=pwd, email=email, blog=blog, **extra)

        else:
            response["msg"] = form.errors

        return JsonResponse(response)

    form = UserForm()

    return render(request, 'register.html', {"form": form})


def get_classication_data(username):
    '''
    分类信息查询模块，不是视图！！
    '''

    user = models.UserInfo.objects.filter(username=username).first()
    blog = user.blog
    article_count_dic = models.Article.objects.filter(user=user).aggregate(c=Count("nid"))
    article_count = article_count_dic.get("c")


    return {"user": user, "blog": blog, "article_count": article_count}


def home_site(request, username, **kwargs):
    '''
    个人站点视图
    '''
    # 判断用户是否存在
    user = models.UserInfo.objects.filter(username=username).first()
    if not user:
        return render(request, '404_notfound.html')
    else:

        # 分类信息查询
        context_classication_data = get_classication_data(username)

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
                article_list = article_list.filter(category__title=param, category__blog=blog).order_by("-nid").all()
            elif condition == "tag":
                print(param)
                article_list = article_list.filter(tags__title=param, tags__blog=blog).order_by("-nid").all()
            elif condition == "archive":
                year, month = param.split("-")
                article_list = article_list.filter(
                    create_time__year=year, create_time__month=month).all()

        # 分页器函数
        context = pageinator_bar(request, article_list, 6)

        context.update(context_classication_data)

        return render(request, "home_site.html", context)


def article_detail(request, username, article_number):
    '''
    文章详情页
    '''
    user = models.UserInfo.objects.filter(username=username).first()
    article = models.Article.objects.filter(
        user=user, nid=article_number).first()
    comments = models.Comment.objects.filter(article=article).all()
    models.PageView.objects.filter(article=article).update(pageview_count=F("pageview_count")+1)

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
    context_classication_data = get_classication_data(username)  # blog user article_count
    articles = models.Article.objects.filter(user = context_classication_data.get("user").nid).order_by("-up_count","-comment_count","-nid").all()
    context = pageinator_bar(request, articles, 15)
    context.update(context_classication_data) # context字典合并context_classication_data字典更新

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
        soup, desc = soup_desc(content)

        article = models.Article.objects.create(title=title, content=str(soup), desc=desc, user=request.user, category_id=category_id)
        models.PageView.objects.create(pageview_count=0, article=article)

        path = os.path.join("/",request.user.username,"backend").replace("\\","/")
        return redirect(path)

    return render(request, 'backend/add_article.html', {"category_list": category_list})

def soup_desc(content):
    '''
    过滤script标签和desc截取视图
    '''
    soup = BeautifulSoup(content, "html.parser")
    # 过滤script标签
    for tag in soup.find_all():
        if tag.name == "script":
            tag.decompose()

    # 获取content中的文本为desc
    desc = soup.text[0:150]
    if len(soup) >= 150:
        desc +=  "..."

    return soup, desc


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
    文章更新视图
    '''
    user = request.user
    article = models.Article.objects.filter(user=request.user, nid=article_number).first()
    category_list = models.Category.objects.filter(blog=user.blog).all()
    active_category_id = models.Category.objects.filter(article__nid=article_number).values("nid").first()

    active_category_id =  active_category_id.get("nid") if active_category_id else ""

    title = article.title
    content = article.content

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        category_id = request.POST.get("category_id")

        # soup防御xss攻击
        soup, desc = soup_desc(content)

        models.Article.objects.filter(user=request.user, nid=article_number).update(title=title,desc=desc, content=str(soup),category_id=category_id)

        path = os.path.join("/", request.user.username, "articles", article_number).replace("\\", "/")

        return redirect(path)

    return render(request, 'backend/upd_article.html', {"title":title, "content":content, "category_list":category_list, "active_category_id":active_category_id })

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