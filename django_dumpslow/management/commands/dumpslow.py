# -*- coding: utf-8 -*-
#
# django-dumpslow -- Django application to log and summarize slow requests
#                    <http://chris-lamb.co.uk/projects/django-dumpslow>
#
# Copyright © 2009 Chris Lamb <chris@chris-lamb.co.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

import os
import re
import sys
import time
import datetime
import fileinput

from glob import glob
from operator import itemgetter
from optparse import make_option

from django.conf import settings
from django.core.urlresolvers import resolve, Resolver404
from django.core.management.base import BaseCommand, CommandError

REQUEST_MATCH = re.compile(
    r'Long request - (?P<duration>[^s]+)s (?P<url>.*)',
)

INTERVAL_MATCH = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?!,\d{3})?',
)

class Command(BaseCommand):
    help = "Parse and summarize the django-dumpslow slow request log"

    option_list = BaseCommand.option_list + (
        make_option('-s', dest='order', metavar='ORDER', default='at',
            help="what to sort by (at, count) (default: at)"),
        make_option('-i', dest='after', metavar='INTERVAL', default=None,
            help="interval to report on (eg. 3d 1w 1y) (default: all)"),
        make_option('-r', dest='reverse', default=False, action='store_true',
            help="reverse the sort order (largest last instead of first)"),
        make_option('-t', dest='limit', default=None, metavar='NUM',
            help="just show the top NUM queries"),
        make_option('-m', dest='max_duration', metavar='SECS', default=20,
            help="ignore entries over SECS seconds (default: 20)"),
    )

    def handle(self, *args, **options):
        files = list(args)

        if not files:
            # If no logfiles are specified, try and use the default logfile name
            try:
                for filename in glob(settings.LONG_REQUEST_LOGS):
                    if os.path.exists(filename):
                        files.append(filename)
            except AttributeError:
                pass

        if not files:
            raise CommandError(
                'No files specified and LONG_REQUEST_LOGS target does not exist.'
            )

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
                after = datetime.datetime.now() - \
                    self.parse_interval(after)
            except ValueError:
                raise CommandError('Invalid interval %r' % after)

        order = options['order']
        if order not in ('at', 'count'):
            raise CommandError('Invalid sort order %r' % options['order'])

        data = {}
        for line in fileinput.input(files):
            match = REQUEST_MATCH.search(line)
            if not match:
                continue

            if after:
                interval_match = INTERVAL_MATCH.search(line)
                if not interval_match:
                    raise CommandError(
                        'You specified a time interval, but not all "long '
                        'request" log lines have a valid time:\n%r' % line[:-1]
                    )

                timeobj = datetime.datetime(*time.strptime(
                    interval_match.group(1),
                    "%Y-%m-%d %H:%M:%S"[0:6],
                ))

                if after and timeobj < after:
                    continue

            try:
                func, args, kwargs = \
                    resolve(match.group('url'), urlconf=settings.ROOT_URLCONF)
                view = "%s.%s" % (func.__module__, func.__name__)
            except Resolver404:
                view = '%s (unreversible url)' % match.group('url')

            duration = float(match.group('duration'))

            if max_duration and duration >= max:
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

        items = data.items()
        del data
        items.sort(key=itemgetter(1), reverse=not options['reverse'])

        if limit:
            items = items[:limit]

        print "", "View",
        print {
            'count': 'Count',
            'at': 'Accumulated time',
        }[order].rjust(66)
        print "", "=" * 71

        for view, duration in items:
            pad = 70 - len(view)

            print "", view,
            if order == 'at':
                print ("%2.2f" % duration).rjust(pad)
            elif order == 'count':
                print str(duration).rjust(pad)

    @classmethod
    def parse_interval(cls, val):
        match = re.match(r'^(\d+)([smhdwy])$', val)
        if not match:
            raise ValueError()

        unit = {
            's': 'seconds',
            'm': 'minutes',
            'h': 'hours',
            'd': 'days',
            'w': 'weeks',
        }[match.group(2)]

        return datetime.timedelta(**{unit: int(match.group(1))})
