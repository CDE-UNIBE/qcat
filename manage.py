#!/usr/bin/env python
import sys
import os

import envdir as envdir

if __name__ == "__main__":
    # Load the environment variables in the folder ``./envs/`` with *envdir*.
    envdir.read(os.path.join(os.path.dirname(__file__), 'envs'))

    if 'test' in sys.argv:
        os.environ.__setitem__('DJANGO_CONFIGURATION', 'TestDefaultSite')

    # Please note that this is *django-configurations* and not *Django*.
    from configurations.management import execute_from_command_line

    execute_from_command_line(sys.argv)
