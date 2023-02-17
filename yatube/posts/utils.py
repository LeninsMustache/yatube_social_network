from django.core.paginator import Paginator

POSTS_ON_ONE_PAGE = 10


def show_paginator(request, post_list,):
    paginator = Paginator(post_list, POSTS_ON_ONE_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
