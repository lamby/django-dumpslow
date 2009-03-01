from django.conf.urls.defaults import *

urlpatterns = patterns('example.views',
   url(r'^$', 'index', name='index'),
   url(r'^slow$', 'slow', name='slow'),
)
