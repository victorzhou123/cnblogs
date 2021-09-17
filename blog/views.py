# python标准库

# 第三方插件库
from blog.models import UserInfo
from django.shortcuts import redirect, render, HttpResponse
from django.contrib import auth    # 超级用户模块
from django.http import JsonResponse

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

    return render(request, 'index.html')

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
