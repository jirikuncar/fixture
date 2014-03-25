#!/usr/bin/env python
from __future__ import absolute_import

import sys
import os

sys.path.append(os.path.dirname(__file__))

from django.core.management import execute_from_command_line


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
