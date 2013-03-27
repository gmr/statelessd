"""
Publishing Request Handler

"""
import base64
import logging

from statelessd import base
from statelessd import rabbitmq

LOGGER = logging.getLogger(__name__)


class Publisher(base.RequestHandler):
    """HTTP -> AMQP Pubishing Request Handler"""
    AUTHENTICATE = 'WWW-Authenticate'
    INT_PROPERTIES = ['delivery_mode', 'priority', 'timestamp']
    PROPERTIES = ['app_id',
                  'content_encoding',
                  'content_type',
                  'correlation_id',
                  'delivery_mode',
                  'expire',
                  'headers',
                  'message_id',
                  'priority',
                  'reply_to',
                  'timestamp',
                  'type',
                  'user_id']
    REALM = 'Basic realm=statelessd'

    def initialize(self):
        """Initial the Request Handler making sure that the connection and
        channel handlers are held in the application scope for this process.

        """
        super(Publisher, self).initialize()
        if not hasattr(self.application, 'rabbitmq'):
            setattr(self.application, 'rabbitmq', dict())
        self.rmq_host = self.rabbitmq_settings.get('host', 'localhost')
        self.rmq_port = int(self.rabbitmq_settings.get('port', 5672))

    @property
    def rabbitmq_settings(self):
        """Return the RabbitMQ settings section from the configuration file

        :rtype: dict

        """
        return self.application.settings.get('rabbitmq', dict)

    def connection_id(self, username, virtual_host):
        """Return a RabbitMQ connection id for the current request

        :param str username: The username for the connection
        :param str virtual_host: The virtual host for the connection
        :rtype: str

        """
        return '%s:%s' % (virtual_host, username)

    def get_rabbitmq(self, username, password, virtual_host):
        """Return a handle to the RabbitMQ object for this request.

        :rtype: RabbitMQ

        """
        connection_id = self.connection_id(username, virtual_host)
        if connection_id not in self.application.rabbitmq.keys():
            rmq = rabbitmq.RabbitMQ(self.rmq_host,
                                    self.rmq_port,
                                    username,
                                    password,
                                    virtual_host)
            self.application.rabbitmq[connection_id] = rmq
        return self.application.rabbitmq[connection_id]

    def prepare(self):
        """Ensure the request is passing a username and password, returning a
        401 if it is not.

        """
        super(Publisher, self).prepare()
        self._username, self._password = None, None
        auth_header = self.request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            return self.send_auth_header()

        auth_decoded = base64.decodestring(auth_header[6:])
        self._username, self._password = auth_decoded.split(':', 2)
        if self._username is None or self._password is None:
            self.send_auth_header()

    def post(self, virtual_host, exchange, routing_key):
        """Handle requests Posted to the server

        :param str virtual_host: The virtual host parsed from the URI
        :param str exchange: The exchange parsed from the URI
        :param str routing_key: The routing key to publish with

        """
        rmq = self.get_rabbitmq(self._username, self._password, virtual_host)

        # Map the properties to a dict for publishing
        properties = dict()
        for key in self.PROPERTIES:
            value = self.get_argument(key, None)
            if value:
                if key in self.INT_PROPERTIES:
                    properties[key] = int(value)
                else:
                    properties[key] = value

        # Publish the message
        try:
            rmq.publish(exchange, routing_key, properties,
                        self.get_argument('body', None))
        except rabbitmq.MessageDeniedError as error:
            LOGGER.critical('Message publish was denied: %s', error)
            # request failed due to failure of a previous request
            return self.set_status(424)

        # Set the status
        self.set_status(204)

    def send_auth_header(self):
        """Send a 401 header with the correct info and finish the request,
        bypassing self.post
        """
        self.set_status(401)
        self.set_header(self.AUTHENTICATE, self.REALM)
        self._transforms = []
        self.finish()
