# -*- coding: utf-8 -*-
#
# django-dumpslow -- Django application to log and summarize slow requests
#                    <http://chris-lamb.co.uk/projects/django-dumpslow>
#
# Copyright © 2009-2010 Chris Lamb <chris@chris-lamb.co.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

import time
import logging
import threading

from django.conf import settings

from django_dumpslow.signals import long_request

class LogLongRequestMiddleware(object):
    def __init__(self):
        self.local = threading.local()

    def process_request(self, request):
        self.local.start_time = time.time()

    def process_response(self, request, response):
        time_taken = time.time() - self.local.start_time

        try:
            max_time = settings.LONG_REQUEST_TIME
        except AttributeError:
            max_time = 1

        if time_taken > max_time:
            url = request.META['PATH_INFO']

            log = logging.getLogger('dumpslow')
            log.warning('Long request - %.3fs %s', time_taken, url)

            long_request.send(
                sender=request,
                url=url,
                request=request,
                response=response,
                time_taken=time_taken,
            )

        return response
