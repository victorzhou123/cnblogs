# python标准库

# 第三方插件库
from django.db.models.aggregates import Count
from blog.models import Category, UserInfo
from django.shortcuts import redirect, render, HttpResponse
from django.contrib import auth    # 超级用户模块
from django.http import JsonResponse
from blog import models
from django.db.models.functions import TruncMonth # 使日期截断至月

# 自建库
from .Myforms import UserForm
from blog.utils.validCode import get_valid_code_img

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
    
    article_list = models.Article.objects.all()

    return render(request, 'index.html', {"article_list":article_list})

def logout(request):

    auth.logout(request) # request.session.flush()

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
            avatar_obj = request.FILES.get("avatar")

            extra = {}
            # 判断用户有没有上传头像
            if avatar_obj:
                extra["avatar"] = avatar_obj

            UserInfo.objects.create(
                username=user, password=pwd, email=email, **extra)

        else:
            response["msg"] = form.errors

        return JsonResponse(response)

    form = UserForm()

    return render(request, 'register.html', {"form": form})

def home_site(request, username, **kwargs):
    '''
    个人站点视图
    '''
    print("username", username)
    if kwargs:
        pass
    else:
        # 判断用户是否存在
        user = UserInfo.objects.filter(username=username).first()
        if not user:
            return render(request, '404_notfound.html')
        else:
            # 获取当前站点信息
            blog = user.blog
            # 获取当前站点的所有文章
            # 基于对象查询
            article_list = user.article_set.all()
            # 基于__查询，JOIN查询
            # article_list = models.Article.objects.filter(user=user).all()

            # 查询当前站点每一个分类的名称以及对应的文章数
            category_list = models.Category.objects.filter(blog=blog).values("nid").annotate(
                                        c=Count("nid")).values_list("title","c")

            # 查询当前站点的每一个标签名称以及对应的文章数
            tag_list = models.Tag.objects.filter(blog=blog).values("nid").annotate(
                                    c=Count("nid")).values_list("title","c")


            # 查询当前站点每一个年月的名称以及对应的文章数
            # date_list = models.Article.objects.filter(user=user).extra(
            #                                    select={"y_m_date":"date_format(create_time,'%%Y-%%m')"}).values(
            #                                        "y_m_date").annotate(c=Count("nid")).values_list(
            #                                         "y_m_date", "c")

            date_list = models.Article.objects.filter(user=user).annotate(
                                            y_m_date=TruncMonth("create_time")).values("y_m_date").annotate(c=Count("nid")).values_list("y_m_date", "c")



            return render(request, "home_site.html", 
                        {"article_list":article_list, "blog":blog, "category_list":category_list,
                        "tag_list":tag_list, "date_list":date_list, })
