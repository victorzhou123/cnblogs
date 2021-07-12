from django.shortcuts import render,HttpResponse



# Create your views here.
from django.http import JsonResponse

def login(request):

    if request.method == 'POST':
        response = {"user":None,"msg":None}
        user = request.POST.get("user")
        pwd = request.POST.get("pwd")
        valid_code = request.POST.get("valid_code")

        if valid_code.upper() == request.session.get("valid_code_str") :
            pass
        else:
            response["msg"] = "valid code error!"
        return JsonResponse(response)

    return render(request,'login.html')


def get_validCode_img(request):
    from PIL import Image,ImageDraw,ImageFont
    import random
    from io import BytesIO

    def get_random_color():
        return (random.randint(0,255),random.randint(0,255),random.randint(0,255))

    '''
    设置背景板
    '''

    img = Image.new('RGB',(255,33),color=get_random_color()) #Image是图像生产工具
    draw = ImageDraw.Draw(img)                               #在img的背景色上写字,改变draw结果保存在img里
    kumo_font = ImageFont.truetype("static/font/kumo.ttf",size=32)

    '''
    保存字符串
    '''

    valid_code_str = ""

    '''
    在背景板上写字
    '''

    for i in range(5):
        random_num = str(random.randint(0,9))
        random_low_alpha = chr(random.randint(95,122))
        random_upper_alpha = chr(random.randint(65,90))
        random_char = random.choice([random_num,random_low_alpha,random_upper_alpha])

        draw.text((i*50+20,2),random_char,get_random_color(),font=kumo_font)
        # 保存验证码字符串
        valid_code_str += random_char


    '''
    在验证码上形成噪点干扰
    '''

    width=270
    height=40
    for i in range(7):
        x1=random.randint(0,width)
        x2=random.randint(0,width)
        y1=random.randint(0,height)
        y2=random.randint(0,height)
        draw.line((x1,y1,x2,y2),fill=get_random_color())

    for i in range(100):
        draw.point([random.randint(0, width), random.randint(0, height)], fill=get_random_color())
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.arc((x, y, x + 4, y + 4), 0, 90, fill=get_random_color())

    """""
    方法一：保存图片到硬盘中
    """""
    # with open("validCode.png","wb") as f:
    #     img.save(f,"png")
    #
    # with open("validCode.png","rb") as f:
    #     data = f.read()

    """""
    方法二：保存到内存中,读写更快
    """""

    #把验证码存到
    request.session["valid_code_str"] = valid_code_str

    f = BytesIO()     #内存管理工具
    img.save(f,"png")
    data = f.getvalue()


    return HttpResponse(data)

def index(request):

    return render(request,'index.html')