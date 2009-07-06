from django.conf.urls.defaults import *

from .views import slow2

urlpatterns = patterns('example.views',
   url(r'^$', 'index', name='index'),
   url(r'^slow$', 'slow', name='slow'),
   url(r'^slow2$', slow2(), name='slow2'),
)
