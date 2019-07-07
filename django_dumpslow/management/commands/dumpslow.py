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

import time
import redis
from tabulate import tabulate

from operator import itemgetter
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from django_dumpslow.utils import parse_interval

class Command(BaseCommand):
    help = "Parse and summarize the django-dumpslow slow request log"

    def add_arguments(self, parser):
        parser.add_argument('-s',
            dest='order',
            default='at',
            help='what to sort by (at, count, average) (default: at)')
        parser.add_argument('-i',
            dest='after',
            default=0,
            help='interval to report on (eg. 3d 1w 1y) (default: all)')
        parser.add_argument('-r',
            action='store_true',
            dest='reverse',
            default=False,
            help='reverse the sort order (largest last instead of first)')
        parser.add_argument('-t',
            dest='limit',
            default=None,
            help='just show the top NUM queries')
        parser.add_argument('-m',
            dest='max_duration',
            default=20,
            help='ignore entries over SECS seconds (default: 20)')

    def handle(self, **options):
        def check_option(name, val):
            try:
                val = int(val)
                if val < 0:
                    raise ValueError()
                return val
            except ValueError:
                raise CommandError(
                    'Invalid value for %s %r' % (name, val)
                )
            except TypeError:
                pass

        limit = check_option('-t', options['limit'])
        max_duration = check_option('-m', options['max_duration'])

        after = options['after']
        if after:
            try:
                after = int(time.time()) - parse_interval(after)
            except ValueError:
                raise CommandError('Invalid interval %r' % after)

        order = options['order']
        if order not in ('at', 'count', 'average'):
            raise CommandError('Invalid sort order %r' % options['order'])

        if getattr(settings, 'REDIS_URL', None):
            client = redis.from_url(settings.REDIS_URL)
        else:
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
            )

        data = {}
        results = client.zrangebyscore(
            getattr(settings, 'DUMPSLOW_REDIS_KEY', 'dumpslow'), after, '+inf',
        )

        for line in results:
            view, duration = line.split(b'\n', 1)

            duration = float(duration)

            if max_duration and duration >= max_duration:
                continue

            try:
                data[view]['at'] += duration
                data[view]['count'] += 1
            except KeyError:
                data[view] = {'at': duration, 'count': 1 }
                
            data[view]['average'] = data[view]['at'] / data[view]['count']

        items = sorted(data.items(), key=lambda item: item[1][order], reverse=not options['reverse'])
        del data

        if limit is not None:
            items = items[:limit]

        headers=['View', 'Count', 'Accumulated time', 'Average time']
        print(tabulate([[view, values['count'], values['at'], values['average']] for view, values in items], headers=headers))
