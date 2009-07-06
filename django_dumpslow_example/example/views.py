import time

from django.http import HttpResponse
from django.shortcuts import render_to_response

def index(request):
    return render_to_response('index.html')

def slow(request):
    time.sleep(2)
    return HttpResponse('This page should have taken >=2s to render.')

class slow2(object):
    def __call__(self, request):
        time.sleep(5)
        return HttpResponse('This page should have taken >=5s to render.')
