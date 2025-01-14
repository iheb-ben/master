from flask_socketio import emit


def handle_message(data):
    print(f'Received message: {data}')
    emit('response', {'message': 'Message received!'})
