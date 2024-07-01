"""Setup program for dnci client.
Usage: setup"""

import os

os.system('mkdir logs')

files_to_create = ['logs/client.log',]

for path in files_to_create:
    with open(path, 'x'):
        pass

print("Setup completed successfully")
