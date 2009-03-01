from django_dumpslow.signals import long_request

def long_request_cb(sender, time_taken, url, request, response, **kwargs):
    print "Slow request detected on %s %.2fs (via signal)" % (url, time_taken)

long_request.connect(long_request_cb)
