from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter
from sockets import routing
from sockets.consumers import DBWriteConsumer

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
    "channel": ChannelNameRouter({
        "db-write": DBWriteConsumer
    }),
})
