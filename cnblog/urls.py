"""cnblog URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from blog import views
from cnblog import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login),
    path('index/', views.index),
    path('', views.index),
    path('register/', views.register),
    path('get_validCode_img/', views.get_validCode_img),
    path('logout/', views.logout),

    # media配置
    re_path(r"media/(?P<path>.*)$", serve,
            {"document_root": settings.MEDIA_ROOT}),
    
    # 个人站点URL
    re_path('^(?P<username>\w+)$', views.home_site),

    # 个人站点内的页面跳转
    # tag category archive跳转
    re_path('^(?P<username>\w+)/(?P<condition>category|tag|archive)/(?P<param>.*)$', views.home_site),

    # 文章详情页
    re_path('^(?P<username>\w+)/articles/(?P<article_number>\d+)$', views.article_detail),


]
