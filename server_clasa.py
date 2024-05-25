import socket
import threading
import json

class FileServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(5)
        self.clients = {}
        self.files = {}

    def broadcast_files(self, exclude_username=None):
        for username, client_socket in self.clients.items():
            if username == exclude_username:
                continue
            other_files = {user: self.files[user] for user in self.files if user != username}
            client_socket.send(json.dumps({'type': 'files_update', 'data': other_files}).encode('utf-8'))

    def notify_new_client(self, new_username, new_files):
        notification = {
            'type': 'new_client',
            'data': {
                'username': new_username,
                'files': new_files
            }
        }
        for username, client_socket in self.clients.items():
            client_socket.send(json.dumps(notification).encode('utf-8'))

    def notify_client_disconnection(self, disconnected_username):
        notification = {
            'type': 'client_disconnected',
            'data': {
                'username': disconnected_username
            }
        }
        for username, client_socket in self.clients.items():
            client_socket.send(json.dumps(notification).encode('utf-8'))

    def notify_new_file(self, username, filename):
        notification = {
            'type': 'new_file',
            'data': {
                'username': username,
                'filename': filename
            }
        }
        for client_username, client_socket in self.clients.items():
            client_socket.send(json.dumps(notification).encode('utf-8'))

    def notify_delete_file(self, username, filename):
        notification = {
            'type': 'delete_file',
            'data': {
                'username': username,
                'filename': filename
            }
        }
        for client_username, client_socket in self.clients.items():
            client_socket.send(json.dumps(notification).encode('utf-8'))

    def handle_client(self, client_socket, address):
        username = None
        try:
            data = client_socket.recv(1024).decode('utf-8')
            auth_data = json.loads(data)
            username = auth_data['username']
            client_files = auth_data['files']

            # Notify all clients about the new client
            self.notify_new_client(username, client_files)

            # Add the new client to the lists after notifying others
            self.clients[username] = client_socket
            self.files[username] = client_files

            # Send the initial list of files from other clients
            other_files = {user: self.files[user] for user in self.files if user != username}
            client_socket.send(json.dumps({'type': 'files_update', 'data': other_files}).encode('utf-8'))

            # Broadcast the updated list of files to all clients except the current one
            self.broadcast_files(exclude_username=username)

            # Keep the connection open to listen for further updates
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                message = json.loads(data)
                if message['type'] == 'disconnect':
                    break
                elif message['type'] == 'request_file':
                    requested_client = message['owner']
                    requested_file = message['filename']
                    if requested_client in self.clients:
                        self.clients[requested_client].send(json.dumps({
                            'type': 'file_request',
                            'from': username,
                            'filename': requested_file
                        }).encode('utf-8'))
                elif message['type'] == 'file_response':
                    requesting_client = message['to']
                    response = message['response']
                    if requesting_client in self.clients:
                        self.clients[requesting_client].send(json.dumps({
                            'type': 'file_delivery',
                            'filename': message['filename'],
                            'response': response
                        }).encode('utf-8'))
                elif message['type'] == 'add_file':
                    new_file = message['filename']
                    self.files[username].append(new_file)
                    self.notify_new_file(username, new_file)
                elif message['type'] == 'delete_file':
                    delete_file = message['filename']
                    if delete_file in self.files[username]:
                        self.files[username].remove(delete_file)
                        self.notify_delete_file(username, delete_file)

            # Confirm disconnection to the client
            client_socket.send(json.dumps({'type': 'disconnected', 'data': 'Session ended'}).encode('utf-8'))

        except Exception as e:
            print(f"Error: {e}")
        finally:
            if username:
                del self.clients[username]
                del self.files[username]
                self.notify_client_disconnection(username)  # Notify other clients
                self.broadcast_files()  # Update other clients
            client_socket.close()

    def start(self):
        print("Server started and listening on port 5555")
        while True:
            client_socket, addr = self.server.accept()
            print(f"Accepted connection from {addr}")
            client_handler = threading.Thread(target=self.handle_client, args=(client_socket, addr))
            client_handler.start()

if __name__ == "__main__":
    server = FileServer()
    server.start()
