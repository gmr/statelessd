"""
dashboard

"""
import logging
from tornado import web

LOGGER = logging.getLogger(__name__)


class Dashboard(web.RequestHandler):

    def get(self, *args, **kwargs):
        self.render('dashboard.html')
