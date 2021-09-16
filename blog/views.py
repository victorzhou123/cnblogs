from django.forms.forms import Form
from django.shortcuts import render,HttpResponse
from django.contrib import auth    # 超级用户模块
from django import forms
from django.forms import widgets


# Create your views here.
from django.http import JsonResponse

def login(request):

    if request.method == 'POST':
        response = {"user":None,"msg":None} # 响应字典
        user = request.POST.get("user")
        pwd = request.POST.get("pwd")
        valid_code = request.POST.get("valid_code")

        # 验证验证码
        valid_code_str = request.session.get("valid_code_str")
        if valid_code.upper() == valid_code_str.upper() :
            # 用户名密码验证
            user = auth.authenticate(username = user, password = pwd)
            if user:
                auth.login(request, user) # request.user == 当前登录对象
                response["user"] = user.username
                response["msg"] = "log in success!"
            else:
                response["msg"] = "username or password error!" # 响应信息
        else:
            response["msg"] = "valid code error!" # 响应信息
        return JsonResponse(response) # 返回响应字典

    return render(request,'login.html')


def get_validCode_img(request):
    '''
    获取验证码图片
    '''
    from blog.utils.validCode import get_valid_code_img

    data = get_valid_code_img(request)

    return HttpResponse(data)

def index(request):

    return render(request,'index.html')


class UserForm(forms.Form):
    user = forms.CharField(max_length = 32, label="用户名",
                            widget = widgets.TextInput(attrs={'class':'form-control'}))
    pwd = forms.CharField(max_length = 32, label="密码",
                            widget = widgets.PasswordInput(attrs={'class':'form-control'}))
    re_pwd = forms.CharField(max_length = 32, label="确认密码",
                            widget = widgets.PasswordInput(attrs={'class':'form-control'}))
    email = forms.EmailField(max_length = 32, label="邮箱",
                            widget = widgets.EmailInput(attrs={'class':'form-control'}))

def register(request):
    if request.is_ajax():
        print(request.POST)
        form = UserForm(request.POST)
        # 构造响应字典
        response = {"user":None, "msg":None}
        if form.is_valid():
            response["user"] = form.cleaned_data.get("user")
        else:
            print(form.cleaned_data)
            print(form.errors)
            response["msg"] = form.errors

        return JsonResponse(response)

    form = UserForm()

    return render(request, 'register.html', {"form":form})