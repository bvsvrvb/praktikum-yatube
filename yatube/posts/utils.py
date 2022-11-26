from django.core.paginator import Paginator


def create_paginator(request, list, NUM):
    paginator = Paginator(list, NUM)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
