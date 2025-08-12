import os
import json
import queue
import secrets
import asyncio
from pipe import Pipe
from blinker import signal
from gmqtt import Client as MQTTClient
import redis.asyncio as aioredis

from ._meta import config, logger
from .setup import on_startup, on_shutdown
from fluvius.auth import event as auth_event
from fluvius.auth.hashes import make_hash


MQTT_DEBUG = config.MQTT_DEBUG
MQTT_CLIENT_QOS = config.MQTT_CLIENT_QOS
MQTT_CLIENT_RETAIN = config.MQTT_CLIENT_RETAIN
MQTT_CLIENT_CHANNEL = config.MQTT_CLIENT_CHANNEL

MQTT_QUEUES = {}


class MqttEvent:
    on_connect = signal("mqtt_connect")
    on_message = signal("mqtt_message")
    on_disconnect = signal("mqtt_disconnect")
    on_subscribe = signal("mqtt_subscribe")


class FastapiMQTTClient(MQTTClient):
    @staticmethod
    def on_connect(self, flags, rc, properties):
        MqttEvent.on_connect.send(self, flags=flags, rc=rc, properties=properties)
        logger.warning(f"/MQTT/ CONNECTED {self._client_id}")
        MQTT_DEBUG and logger.info(f"/MQTT/ CONNECTED {self._client_id}")

    def on_message(self, topic, payload, qos, properties):
        MqttEvent.on_message.send(
            self, topic=topic, payload=payload, qos=qos, properties=properties
        )
        MQTT_DEBUG and logger.info(
            f"/MQTT/ RECV MSG AT [{self._client_id}] TOPIC [{topic}] "
            f"/MQTT/ QOS: {qos} PROPERTIES: {properties} PAYLOAD: {payload}"
        )

    @staticmethod
    def on_disconnect(self, packet, exc=None):
        MqttEvent.on_disconnect.send(self, packet=packet, exc=exc)
        MQTT_DEBUG and logger.info(f"/MQTT/ DISCONNECTED {self._client_id}")

    @staticmethod
    def on_subscribe(self, mid, qos, properties):
        MqttEvent.on_subscribe.send(self, mid=mid, qos=qos, properties=properties)
        MQTT_DEBUG and logger.info(f"/MQTT/ SUBSCRIBED [{self._client_id}] QOS: {qos}")

    def notify(self, user_id, kind: str, target: str, msg: dict, batch_id=None):
        payl = json.dumps(dict(**msg, _kind=kind, _target=target))
        chan = f"{user_id}/{MQTT_CLIENT_CHANNEL}"

        if batch_id is None:
            return self.publish(
                chan, payl, qos=MQTT_CLIENT_QOS, retain=MQTT_CLIENT_RETAIN
            )

        if batch_id not in MQTT_QUEUES:
            MQTT_QUEUES[batch_id] = queue.Queue()

        q = MQTT_QUEUES[batch_id]
        return q.put((chan, payl))

    def send(self, batch_id):
        try:
            q = MQTT_QUEUES.pop(batch_id)
            while not q.empty():
                chan, payl = q.get()
                self.publish(chan, payl, qos=MQTT_CLIENT_QOS, retain=MQTT_CLIENT_RETAIN)
                q.task_done()
            logger.info("/MQTT/ Published queued messages of context: %s", batch_id)
        except KeyError:
            logger.warn("/MQTT/ Message queue for context_id: %s not found", batch_id)


def configure_mqtt_client(app, client_channel=None):
    if hasattr(app.state, 'mqtt_client'):
        logger.info("/MQTT/ MQTT client already configured")
        return app

    global MQTT_CLIENT_CHANNEL
    if not config.MQTT_BROKER_HOST:
        logger.warn(
            "/MQTT/ MQTT_BROKER_HOST is not set. MQTT client is not configured."
        )
        return app

    MQTT_BROKER_HOST = config.MQTT_BROKER_HOST
    MQTT_BROKER_PORT = config.MQTT_BROKER_PORT

    MQTT_CLIENT_USER = config.MQTT_CLIENT_USER
    MQTT_CLIENT_SECRET = config.MQTT_CLIENT_SECRET

    MQTT_CLIENT_CHANNEL = client_channel or config.MQTT_CLIENT_CHANNEL

    client_id = f"fastapi-{os.getpid()}-{secrets.token_hex(12)}"
    client = FastapiMQTTClient(client_id)
    client.set_auth_credentials(MQTT_CLIENT_USER, MQTT_CLIENT_SECRET)

    app.state.mqtt_client = client

    @on_startup
    async def connect_mqtt(app):
        await app.state.mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
        logger.info(f"/MQTT/ Connected to MQTT broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")

    @on_shutdown
    async def disconnect_mqtt(app):
        await app.state.mqtt_client.disconnect()
        logger.info("/MQTT/ Disconnected from MQTT broker")

    return app


def configure_mqtt_auth(app):
    MQTT_USER_PREFIX = config.MQTT_USER_PREFIX
    MQTT_PERMISSIONS = config.MQTT_PERMISSIONS
    MQTT_DEBUG = config.MQTT_DEBUG
    MQTT_AUTH_PREFIX = f"{MQTT_USER_PREFIX}-auth"
    MQTT_ACL_PREFIX = f"{MQTT_USER_PREFIX}-acl"

    def auth_key(user):
        return f"{MQTT_AUTH_PREFIX}:{user['session_id']}"

    def acl_key(user, channel):
        return f"{MQTT_ACL_PREFIX}:{user['session_id']}:{user['sub']}/{channel}"

    # @TODO: Handling token expiration and user logout
    def authorize_user(user):
        yield (auth_key(user), make_hash(user["client_token"]))
        for chn, perm in MQTT_PERMISSIONS:
            yield (acl_key(user, chn), perm)
        logger.info(f"/MQTT/ Authorized user: {user['sub']} => {user['client_token']}")

    def deauthorize_user(user):
        yield auth_key(user)
        for chn, _ in MQTT_PERMISSIONS:
            yield acl_key(user, chn)
        MQTT_DEBUG and logger.info(f"/MQTT/ De-authorized user: {user}")

    def mqtt_auth(sender, user, **kwargs):
        ops = (
            asyncio.create_task(app.state.mqtt_session.set(k, v))
            for k, v in authorize_user(user)
        )
        asyncio.gather(*ops)

    def mqtt_deauth(sender, user, **kwargs):
        ops = (
            asyncio.create_task(app.state.mqtt_session.delete(k))
            for k in deauthorize_user(user)
        )
        asyncio.gather(*ops)

    @on_startup
    async def setup_mqtt_redis(app) -> None:
        # Initialize aioredis client
        redis_url = getattr(config, 'REDIS_URL', 'redis://localhost:6379')
        app.state.mqtt_session = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        logger.info("/MQTT/ Redis client initialized successfully")

    @on_shutdown
    async def cleanup_mqtt_redis(app) -> None:
        # Close Redis connection
        if hasattr(app.state, 'mqtt_session'):
            await app.state.mqtt_session.close()
            logger.info("/MQTT/ Redis client closed successfully")

    @on_startup
    async def setup_mqtt(app) -> None:
        auth_event.authorization_success.connect(mqtt_auth, weak=False)
        auth_event.user_logout.connect(mqtt_deauth, weak=False)
        logger.info("/MQTT/ User Authorization Handler setup successfully")

    return app

@Pipe
def configure_mqtt(app):
    app = configure_mqtt_client(app)
    app = configure_mqtt_auth(app)
    return app