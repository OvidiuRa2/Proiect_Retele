import socket
import json
import threading
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileClient:
    def __init__(self, username, directory, host='127.0.0.1', port=5555):
        self.username = username
        self.directory = directory
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))
        self.client_files = []
        self.connected = True 
    def get_file_list(self):
        return [f for f in os.listdir(self.directory) if os.path.isfile(os.path.join(self.directory, f))]

    def receive_updates(self):
        while self.connected:
            try:
                data = self.client.recv(1024).decode('utf-8')
                if data:
                    message = json.loads(data)
                    if message['type'] == 'files_update':
                        other_files = message['data']
                        for user, user_files in other_files.items():
                            print(f"\n{user} has published the following files:")
                            for file in user_files:
                                print(f" - {file}")
                    elif message['type'] == 'new_client':
                        new_client = message['data']
                        username = new_client['username']
                        files = new_client['files']
                        print(f"\nNew client {username} has connected.")
                        print(f"{username} has published the following files:")
                        for file in files:
                            print(f" - {file}")
                    elif message['type'] == 'client_disconnected':
                        disconnected_client = message['data']['username']
                        print(f"\nClient {disconnected_client} has disconnected.")
                       
                        if disconnected_client in self.client_files:
                            del self.client_files[disconnected_client]
                    elif message['type'] == 'file_transfer_request':
                        filename = message['filename']
                        requester = message['from']
                        file_path = os.path.join(self.directory, filename)
                        if os.path.isfile(file_path):
                            with open(file_path, 'rb') as f:
                                file_content = f.read()
                            self.client.send(json.dumps({
                                'type': 'file_delivery',
                                'to': requester,
                                'filename': filename,
                                'content': file_content.decode('utf-8')
                            }).encode('utf-8'))
                    elif message['type'] == 'file_delivery':
                        filename = message['filename']
                        content = message['content']
                        file_path = os.path.join(self.directory, filename)
                        with open(file_path, 'wb') as f:
                            f.write(content.encode('utf-8'))
                        print(f"\nYou have received and saved the file {filename}.")
                        self.client_files.append(filename)
                    elif message['type'] == 'new_file':
                        username = message['data']['username']
                        filename = message['data']['filename']
                        print(f"\n{username} has added a new file: {filename}")
                        self.client_files.append(filename)
                    elif message['type'] == 'delete_file':
                        username = message['data']['username']
                        filename = message['data']['filename']
                        print(f"\n{username} has deleted the file: {filename}")
                        if filename in self.client_files:
                            self.client_files.remove(filename)
                    elif message['type'] == 'disconnected':
                        print("\nServer has confirmed your disconnection.")
                        self.connected = False
                        break
            except Exception as e:
                if self.connected:   
                    print(f"Error in receive_updates: {e}")
                break

    def send_commands(self):
        while self.connected:
            command = input("\nAvailable commands:\n - exit (to end the session)\n - request (to request a file)\n - directory (to see the directory)\n ")
            if command.lower() == 'exit':
                self.client.send(json.dumps({'type': 'disconnect'}).encode('utf-8'))
                self.connected = False
                break
            elif command.lower() == 'request':
                owner = input("Enter the owner of the file: ")
                filename = input("Enter the filename: ")
                self.client.send(json.dumps({
                    'type': 'request_file',
                    'owner': owner,
                    'filename': filename
                }).encode('utf-8'))
            elif command.lower() == 'directory':
                print("\nYour published files:")
                for file in self.get_file_list():
                    print(f" - {file}")
                print("\nFiles received:")
                for file in self.client_files:
                    print(f" - {file}")

    def authenticate_and_publish(self):
        auth_data = {
            'username': self.username,
            'files': self.get_file_list()
        }
        self.client.send(json.dumps(auth_data).encode('utf-8'))

        update_thread = threading.Thread(target=self.receive_updates)
        update_thread.daemon = True
        update_thread.start()

        command_thread = threading.Thread(target=self.send_commands)
        command_thread.start()

        command_thread.join()
        self.connected = False
        update_thread.join()
        self.client.close()

    def start_monitoring(self):
        event_handler = FileSystemEventHandler()
        
        def on_created(event):
            if event.is_directory:
                return
            filename = os.path.basename(event.src_path)
            self.client.send(json.dumps({
                'type': 'add_file',
                'filename': filename
            }).encode('utf-8'))
            print(f"File created: {filename}")
            self.client_files.append(filename)

        def on_deleted(event):
            if event.is_directory:
                return
            filename = os.path.basename(event.src_path)
            self.client.send(json.dumps({
                'type': 'delete_file',
                'filename': filename
            }).encode('utf-8'))
            print(f"File deleted: {filename}")
            if filename in self.client_files:
                self.client_files.remove(filename)

        event_handler.on_created = on_created
        event_handler.on_deleted = on_deleted

        observer = Observer()
        observer.schedule(event_handler, self.directory, recursive=False)
        observer.start()

if __name__ == "__main__":
    username = input("Enter your username: ")
    directory = input("Enter the directory to monitor: ")
    client = FileClient(username, directory)
    client.authenticate_and_publish()
    client.start_monitoring()
