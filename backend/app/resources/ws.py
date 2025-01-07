from flask_socketio import Namespace, emit
from app.services.websocket_service import handle_message


# noinspection PyMethodMayBeStatic
class WebSocket(Namespace):
    def on_connect(self):
        emit('message', {'data': 'Connected successfully!'}, broadcast=True, include_self=False)
        print('Client connected')

    def on_disconnect(self):
        emit('message', {'data': 'Connected successfully!'}, broadcast=True, include_self=False)

    def on_custom_event(self, data):
        handle_message(data)
