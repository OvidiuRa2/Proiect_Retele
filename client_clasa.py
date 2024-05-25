import socket
import json
import threading

class FileClient:
    def __init__(self, username, files, host='127.0.0.1', port=5555):
        self.username = username
        self.files = files
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))
        self.client_files = []

    def receive_updates(self):
        while True:
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
                    elif message['type'] == 'file_request':
                        filename = message['filename']
                        requester = message['from']
                        print(f"\nClient {requester} has requested the file {filename}.")
                        # response = input(f"Do you want to send the content of {filename} to {requester}? (yes/no): ")
                        print(f"Do you want to send the content of {filename} to {requester}? (yes/no)")
                        self.client.send(json.dumps({
                            'type': 'file_response',
                            'to': requester,
                            'filename': filename,
                            'response': 'yes'
                        }).encode('utf-8'))
                    elif message['type'] == 'file_delivery':
                        filename = message['filename']
                        response = message['response']
                        if response == 'yes':
                            print(f"\nYou have received the content of the file {filename}.")
                            self.client_files.append(filename)
                        else:
                            print(f"\nThe request for the file {filename} was denied.")
                    elif message['type'] == 'new_file':
                        username = message['data']['username']
                        filename = message['data']['filename']
                        print(f"\n{username} has added a new file: {filename}")
                    elif message['type'] == 'delete_file':
                        username = message['data']['username']
                        filename = message['data']['filename']
                        print(f"\n{username} has deleted the file: {filename}")
            except Exception as e:
                print(f"Error in receive_updates: {e}")
                break

    def send_commands(self):
        while True:
            command = input("\nAvailable commmands:\n - exit (to end the session)\n - request  (to request a file)\n - directory  (to see the directory)\n - add  (to add a new file)\n - delete (to delete a file)\n ")
            if command.lower() == 'exit':
                self.client.send(json.dumps({'type': 'disconnect'}).encode('utf-8'))
                self.client.close()
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
                for file in self.files:
                    print(f" - {file}")
                print("\nFiles received:")
                for file in self.client_files:
                    print(f" - {file}")
            elif command.lower() == 'add':
                new_file = input("Enter the name of the new file: ")
                self.files.append(new_file)
                self.client.send(json.dumps({
                    'type': 'add_file',
                    'filename': new_file
                }).encode('utf-8'))
            elif command.lower() == 'delete':
                delete_file = input("Enter the name of the file to delete: ")
                if delete_file in self.files:
                    self.files.remove(delete_file)
                    self.client.send(json.dumps({
                        'type': 'delete_file',
                        'filename': delete_file
                    }).encode('utf-8'))
                else:
                    print("File not found in your directory.")

    def authenticate_and_publish(self):
        auth_data = {
            'username': self.username,
            'files': self.files
        }
        self.client.send(json.dumps(auth_data).encode('utf-8'))

        # Start a thread to listen for updates from the server
        update_thread = threading.Thread(target=self.receive_updates)
        update_thread.daemon = True
        update_thread.start()

        # Start a thread to handle user commands
        command_thread = threading.Thread(target=self.send_commands)
        command_thread.start()

if __name__ == "__main__":
    username = input("Enter your username: ")
    files = input("Enter your files (comma separated): ").split(',')
    client = FileClient(username, files)
    client.authenticate_and_publish()
