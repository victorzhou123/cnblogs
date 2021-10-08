from django.forms import widgets, ValidationError
from django import forms
from blog import models


class UserForm(forms.Form):
    user = forms.CharField(max_length=32,
                           error_messages={"required": "该字段不能为空"},
                           label="用户名",
                           widget=widgets.TextInput(
                               attrs={'class': 'form-control'}))
    pwd = forms.CharField(max_length=32,
                          error_messages={"required": "该字段不能为空"},
                          label="密码",
                          widget=widgets.PasswordInput(
                              attrs={'class': 'form-control'}))
    re_pwd = forms.CharField(max_length=32,
                             error_messages={"required": "该字段不能为空"},
                             label="确认密码",
                             widget=widgets.PasswordInput(
                                 attrs={'class': 'form-control'}))
    email = forms.EmailField(max_length=32,
                             error_messages={"required": "该字段不能为空"},
                             label="邮箱",
                             widget=widgets.EmailInput(
                                 attrs={'class': 'form-control'}))

    def clean_user(self):
        '''
        局部钩子：校验user是否已经存在
        '''
        val = self.cleaned_data.get("user")
        user = models.UserInfo.objects.filter(username=val).first()

        if not user:
            return val
        else:
            raise ValidationError("该用户已存在！")

    def clean(self):
        '''
        全局钩子：校验两次密码输入是否一致
        '''
        pwd = self.cleaned_data.get("pwd")
        re_pwd = self.cleaned_data.get("re_pwd")

        if pwd and re_pwd:
            if pwd == re_pwd:
                return self.cleaned_data
            else:
                raise ValidationError("两次密码输入不一致！")
        else:
            return self.cleaned_data
