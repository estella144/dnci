"""Setup program for dnci server.
Usage: setup"""

import os

os.system('mkdir logs')

files_to_create = ['logs/client.log',
                   'data/users.json',
                   'data/messages.json',]

for path in files_to_create:
    with open(path, 'x'):
        pass

print("Setup completed successfully")
