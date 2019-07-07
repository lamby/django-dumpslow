# -*- coding: utf-8 -*-
#
# django-dumpslow -- Django application to log and summarize slow requests
#                    <http://chris-lamb.co.uk/projects/django-dumpslow>
#
# Copyright © 2009-2019 Chris Lamb <chris@chris-lamb.co.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

import sys
import time
import redis
import threading

from django.conf import settings
from django.core.mail import mail_admins
from django.utils.deprecation import MiddlewareMixin

from django_dumpslow.utils import parse_interval

class LogLongRequestMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.local = threading.local()
        super().__init__(get_response=get_response)

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
        try:
            view = self.local.view
            time_taken = time.time() - self.local.start_time
        except AttributeError:
            # If, for whatever reason, the variables are not available, don't
            # do anything else.
            return response

        if time_taken < getattr(settings, 'DUMPSLOW_LONG_REQUEST_TIME', 1):
            return response

        if getattr(settings, 'REDIS_URL', None):
            client = redis.from_url(settings.REDIS_URL)
        else:
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
            )

        map_key = '%s\n%.3f' % (view, time_taken)
        mapping = { map_key: self.local.start_time }
        client.zadd(
            getattr(settings, 'DUMPSLOW_REDIS_KEY', 'dumpslow'),
            mapping,
        )

        # Clean up old values

        delete_after = parse_interval(
            getattr(settings, 'DUMPSLOW_DELETE_AFTER', '4w'),
        )

        client.zremrangebyscore(
            getattr(settings, 'DUMPSLOW_REDIS_KEY', 'dumpslow'),
            0,
            int(time.time()) - delete_after,
        )

        # If it was really slow, email admins. Disabled by default.
        email_threshold = getattr(settings, 'DUMPSLOW_EMAIL_REQUEST_TIME', sys.maxsize)
        if time_taken > email_threshold:
            mail_admins(
                "SLOW PAGE: %s" % request.path,
                "This page took %2.2f seconds to render, which is over the threshold "
                "threshold of %s.\n\n%s" % (
                    time_taken,
                    email_threshold,
                    str(request),
                ),
            )

        return response
