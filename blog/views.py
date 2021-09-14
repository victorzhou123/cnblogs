from django.shortcuts import render,HttpResponse
from django.contrib import auth    # 超级用户模块



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
    from blog.utils.validCode import get_valid_code_img

    data = get_valid_code_img(request)

    return HttpResponse(data)

def index(request):

    return render(request,'index.html')