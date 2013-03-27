"""
rabbitmq

"""
import collections
import logging
import pika
from pika.adapters import tornado_connection as pika_adapter
import sys

LOGGER = logging.getLogger(__name__)


class RabbitMQ(object):
    """Container class for dealing with publishing to RabbitMQ negotiating the
    connection, re-connections, etc.

    """
    CONN_OPENED = 'connection_opened'
    CONN_CLOSED = 'connection_closed'
    CHAN_OPENED = 'channel_opened'
    CHAN_CLOSED = 'channel_closed'
    PUBLISHED = 'published'
    RECONNECT_DELAY = 5
    MAX_ATTEMPTS = 10

    COUNTERS = [CONN_OPENED, CONN_CLOSED, CHAN_OPENED, CHAN_CLOSED, PUBLISHED]

    def __init__(self, host, port, username, password, virtual_host):
        """Create a new instance of the RabbitMQ object and connect to RabbitMQ

        :param str host: The host to connect to
        :param int port: The port to use
        :param str username: The username to connect with
        :param str password: The password to use in connecting
        :param str virtual_host: The virtual host to connect to

        """
        self._attempts = 0
        self._channel = None
        self._connection = None
        self._deny_messages = False
        self._host = host
        self._port = port
        self._queued_messages = list()
        self._username = username
        self._password = password
        self._virtual_host = virtual_host

        # Initialize the counters
        if sys.version_info < (2, 7, 0):
            self._counters = dict()
        else:
            self._counters = collections.Counter()
        for key in self.COUNTERS:
            self._counters[key] = 0

        # Connect to RabbitMQ
        self._connection = self._connect()

    def publish(self, exchange, routing_key, properties, body):
        """Publish the message

        :param str exchange: The exchange to publish on
        :param str routing_key: The routing key to use
        :param dict properties: A dictionary of properties
        :param str body: The message body

        """
        if self._deny_messages:
            raise MessageDeniedError('Too many connection attempts: %i' %
                                     self._attempts)
        if not self._channel or not self._channel.is_open:
            self._queued_messages.append((exchange,
                                          routing_key,
                                          pika.BasicProperties(**properties),
                                          body))
            return
        self._publish_message(exchange,
                              routing_key,
                              pika.BasicProperties(**properties),
                              body)

    @property
    def stats(self):
        """Return the current state of the connection and the stats counters.

        :rtype: dict

        """
        return {'connected': self._channel and self._channel.is_open,
                'connections': {'opened': self._counters[self.CONN_OPENED],
                                'closed': self._counters[self.CONN_CLOSED]},
                'channels': {'opened': self._counters[self.CHAN_OPENED],
                             'closed': self._counters[self.CHAN_CLOSED]},
                'publishes': self._counters[self.PUBLISHED],
                'queue_size': len(self._queued_messages)}

    def _connect(self):
        """Connect to RabbitMQ"""
        LOGGER.info("Connecting to %s:%s:%s as %s",
                    self._host, self._port, self._virtual_host, self._username)
        conn = pika.ConnectionParameters(self._host,
                                         self._port,
                                         self._virtual_host,
                                         pika.PlainCredentials(self._username,
                                                               self._password),
                                         connection_attempts=2)
        return pika_adapter.TornadoConnection(conn,
                                              self._on_connect,
                                              self._on_connection_error,
                                              self._on_connection_closed)

    def _on_connect(self, connection_unused):
        """Invoked when RabbitMQ has opened the connection. Once open, open a
        channel to publish messages on.

        :param pika.connection.Connection connection_unused: Opened connection

        """
        LOGGER.info("Connecting to %s:%s:%s as %s",
                    self._host, self._port, self._virtual_host, self._username)
        self._counters[self.CONN_OPENED] += 1
        self._connection.channel(self._on_channel_open)
        # Reset the attempts counter
        self._deny_messages = False
        self._attempts = 0

    def _on_connection_closed(self, connection, reply_code, reply_text):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection
        :param int reply_code: The reply_code from RabbitMQ
        :param str reply_text: The reply_text from RabbitMQ

        """
        LOGGER.warning('Server closed connection, reopening: (%s) %s',
                       reply_code, reply_text)
        self._counters[self.CONN_CLOSED] += 1
        self._channel = None
        self._connection.add_timeout(self.RECONNECT_DELAY, self._reconnect)

    def _on_channel_closed(self, channel, reply_code, reply_text):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel channel: The channel that was closed
        :param int reply_code: The reply_code from RabbitMQ
        :param str reply_text: The reply_text from RabbitMQ

        """
        LOGGER.warning('Channel was closed: (%s) %s',
                       reply_code, reply_text)
        self._channel = None
        self._counters[self.CHAN_CLOSED] += 1
        self._connection.channel(self._on_channel_open)

    def _on_channel_open(self, channel):
        """Called when RabbitMQ has opened the channel. Once open, publish
        any queued messages.

        :param pika.channel.Channel channel: The channel that was opened

        """
        LOGGER.info("Channel opened for %s:%s:%s",
                    self._host, self._port, self._virtual_host)
        self._channel = channel
        self._counters[self.CHAN_OPENED] += 1
        self._channel.add_on_close_callback(self._on_channel_closed)
        self._publish_queued_messages()

    def _on_connection_error(self, connection):
        """Invoked by pika when TornadoConnection is unable to connect to the
        RabbitMQ server.

        """
        self._deny_messages = True
        LOGGER.critical('Could not connect to amqp://%s:%s@%s:%s/%s',
                        self._username, self._password, self._host,
                        self._password, self._virtual_host)
        if self._attempts < self.MAX_ATTEMPTS:
            LOGGER.info('Trying again in %i seconds', self.RECONNECT_DELAY)
            connection.add_timeout(self.RECONNECT_DELAY, self._reconnect)
        else:
            LOGGER.critical('Giving up after %i attempts to connect to '
                            'amqp://%s:%s@%s:%s/%s', self._attempts,
                            self._username, self._password, self._host,
                            self._password, self._virtual_host)

    def _publish_message(self, exchange, routing_key, properties, body):
        """Actually send the message to RabbitMQ

        :param str exchange: The exchange to publish on
        :param str routing_key: The routing key to use
        :param pika.BasicProperties properties: The properties object
        :param str body: The message body

        """
        self._channel.basic_publish(exchange, routing_key, body, properties)
        self._counters[self.PUBLISHED] += 1

    def _publish_queued_messages(self):
        """Called when the RabbitMQ connection and channel has been opened to
        send the messages that could not be sent when the broker was not
        connected.

        """
        LOGGER.info('Channel opened, sending %i queued messages',
                    len(self._queued_messages))
        while self._queued_messages:
            self._publish_message(*self._queued_messages.pop(0))
        LOGGER.info('All queued messages have been sent')

    def _reconnect(self):
        """Invoked by the Tornado IOLoop timer to reconnect to RabbitMQ. The
        timer is started in the _on_connection_closed method.

        """
        self._attempts += 1
        self._connection.connect()


class MessageDeniedError(Exception):
    """Raised when the RabbitMQ class will no longer accept messages to buffer
    or deliver.

    """
    def __repr__(self):
        return '<%s reason="%s">' % (self.__class__.__name__, self.args[0])
