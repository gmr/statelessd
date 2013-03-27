"""
stats

"""
import logging
import resource
import time

from statelessd import base

LOGGER = logging.getLogger(__name__)


class Stats(base.RequestHandler):
    """Gather stats counters from RabbitMQ objects and return as JSON object"""

    def initialize(self):
        """Initial the Request Handler making sure that the connection and
        channel handlers are held in the application scope for this process.

        """
        super(Stats, self).initialize()
        if not hasattr(self.application, 'rabbitmq'):
            setattr(self.application, 'rabbitmq', dict())

    def _base_stats(self):
        """Return base stats including resource utilization for this process.

        :rtype: dict

        """
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {'host': self.application.host,
                'port': self.application.port,
                'requests': self.application.counters,
                'timestamp': int(time.time()),
                'block': {'input': usage.ru_inblock,
                          'output': usage.ru_oublock},
                'context_switches': usage.ru_nvcsw + usage.ru_nivcsw,
                'cpu_time': {'user': usage.ru_utime,
                             'system': usage.ru_stime},
                'memory_usage': usage.ru_maxrss,
                'page_faults': {'minor': usage.ru_minflt,
                                'major': usage.ru_majflt},
                'page_size':  resource.getpagesize(),
                'signals_received': usage.ru_nsignals,
                'swap_outs': usage.ru_nswap}

    def get(self, *args, **kwargs):
        """Get the stats, returning a JSON object with the info.

        :param tuple args: positional arguments
        :param dict kwargs: keyword arguments

        """
        output = self._base_stats()
        output['connections'] = dict()
        for key in self.application.rabbitmq.keys():
            output['connections'][key] = self.application.rabbitmq[key].stats
        self.write(output)
