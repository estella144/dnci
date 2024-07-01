"""Setup program for dnci client.
Usage: setup"""

import os

os.system('mkdir logs')

files_to_create = ['logs/client.log',
                   'data/users.json',
                   'data/messages.json',]

with open('logs/client.log', 'x'):
    pass
