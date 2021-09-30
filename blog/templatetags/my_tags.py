from django import template
from blog import models
from django.db.models import Count
from django.db.models.functions import TruncMonth

register = template.Library()

@register.inclusion_tag("classfication.html")       # 可以传入classfication.html的模板
def get_classification_style(user):
    
    blog = user.blog
    article_count_dic = models.Article.objects.filter(
        user=user).aggregate(c=Count("nid"))
    article_count = article_count_dic.get("c")
    # 查询当前站点每一个分类的名称以及对应的文章数
    category_list = models.Category.objects.filter(blog=blog).values("nid").annotate(
        c=Count("article__title")).values_list("title", "c")

    # 查询当前站点的每一个标签名称以及对应的文章数
    tag_list = models.Tag.objects.filter(blog=blog).values("nid").annotate(
        c=Count("article__nid")).values_list("title", "c")

    # 查询当前站点每一个年月的名称以及对应的文章数
    # date_list = models.Article.objects.filter(user=user).extra(
    #                                    select={"y_m_date":"date_format(create_time,'%%Y-%%m')"}).values(
    #                                        "y_m_date").annotate(c=Count("nid")).values_list(
    #                                         "y_m_date", "c")

    date_list = models.Article.objects.filter(user=user).annotate(
        y_m_date=TruncMonth("create_time")).values("y_m_date").annotate(c=Count("nid")).values_list("y_m_date", "c")

    return {"user": user, "blog": blog, "category_list": category_list, "article_count": article_count,
            "tag_list": tag_list, "date_list": date_list}
