# -*- coding: utf-8 -*-
#
# django-dumpslow -- Django application to log and summarize slow requests
#                    <http://chris-lamb.co.uk/projects/django-dumpslow>
#
# Copyright © 2009-2011 Chris Lamb <chris@chris-lamb.co.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

import re
import time
import redis

from operator import itemgetter
from optparse import make_option

from django.conf import settings
from django.core.management.base import NoArgsCommand, CommandError

from django_dumpslow.utils import parse_interval

class Command(NoArgsCommand):
    help = "Parse and summarize the django-dumpslow slow request log"

    option_list = NoArgsCommand.option_list + (
        make_option('-s', dest='order', metavar='ORDER', default='at',
            help="what to sort by (at, count, average) (default: at)"),
        make_option('-i', dest='after', metavar='INTERVAL', default=0,
            help="interval to report on (eg. 3d 1w 1y) (default: all)"),
        make_option('-r', dest='reverse', default=False, action='store_true',
            help="reverse the sort order (largest last instead of first)"),
        make_option('-t', dest='limit', default=None, metavar='NUM',
            help="just show the top NUM queries"),
        make_option('-m', dest='max_duration', metavar='SECS', default=20,
            help="ignore entries over SECS seconds (default: 20)"),
    )

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

        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
        )

        data = {}
        totals = {}
        hits = {}
        results = client.zrangebyscore(
            getattr(settings, 'DUMPSLOW_REDIS_KEY', 'dumpslow'), after, '+inf',
        )

        for line in results:
            view, duration = line.split('\n', 1)

            duration = float(duration)

            if max_duration and duration >= max_duration:
                continue

            if order == 'at':
                try:
                    data[view] += duration
                except KeyError:
                    data[view] = duration

            elif order == 'count':
                try:
                    data[view] += 1
                except KeyError:
                    data[view] = 1

            elif order == 'average':
                try:
                    totals[view] += duration
                    hits[view] += 1
                except KeyError:
                    totals[view] = duration
                    hits[view] = 1

                data[view] = totals[view] / hits[view]


        items = data.items()
        del data
        items.sort(key=itemgetter(1), reverse=not options['reverse'])

        if limit is not None:
            items = items[:limit]

        print "", "View",
        print {
            'count': 'Count',
            'at': 'Accumulated time',
            'average': 'Average time',
        }[order].rjust(66)
        print "", "=" * 71

        for view, value in items:
            pad = 70 - len(view)

            print "", view,
            if order == 'at':
                print ("%2.2f" % value).rjust(pad)
            elif order == 'count':
                print str(value).rjust(pad)
            elif order == 'average':
                print ("%2.2f" % value).rjust(pad)
