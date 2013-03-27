"""
Base Request Handler

"""
import collections
import logging
import sys
import time
from tornado import web

LOGGER = logging.getLogger(__name__)


class RequestHandler(web.RequestHandler):
    """Base RequestHandler that ensures that the request counters are created
    and that counts are collected per request.

    """
    DURATION = 'processing_time'

    def increment_counter(self, counter, value=1):
        """Increment the counter specified

        """
        try:
            self.application.counters[counter] += value
        except KeyError:
            self.application.counters[counter] = value

    def initialize(self):
        if not hasattr(self.application, 'counters'):
            self.initialize_counters()

    def initialize_counters(self):
        if not hasattr(self.application, 'counters'):
            if sys.version_info < (2, 7, 0):
                counters = dict()
            else:
                counters = collections.Counter()
            setattr(self.application, 'counters', counters)

    def prepare(self):
        """Initialize the request counters if the application does not have
        a counters attribute.

        """
        self.increment_counter('method.%s' % self.request.method)

    def on_finish(self):
        """Increment the request time counter"""
        self.increment_counter(self.DURATION,
                               time.time() - self.request._start_time)
        self.increment_counter('response.%s' % self.get_status())
