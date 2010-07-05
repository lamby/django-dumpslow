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
import redis
import threading

from django.conf import settings

class LogLongRequestMiddleware(object):
    def __init__(self):
        self.local = threading.local()

    def process_view(self, request, callback, callback_args, callback_kwargs):
        view = '%s.' % callback.__module__

        try:
            view += callback.__name__
        except (AttributeError, TypeError):
            # Some view functions (eg. class-based views) do not have a
            # __name__ attribute; try and get the name of its class
            view += callback.__class__.__name__

        self.local.view = view
        self.local.start_time = time.time()

    def process_response(self, request, response):
        time_taken = time.time() - self.local.start_time

        if time_taken < getattr(settings, 'DUMPSLOW_LONG_REQUEST_TIME', 1):
            return response

        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
        )

        client.zadd(
            getattr(settings, 'DUMPSLOW_REDIS_KEY', 'dumpslow'),
            '%s\n%.3f' % (self.local.view, time_taken),
            self.local.start_time,
        )

        return response
