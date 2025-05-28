import sys
import shutil
import pathlib
import logging
import os

from contextlib import chdir

logger = logging.getLogger(__name__)

from .utils import system
from .getversion import setVersion

# This function is called with just the Python standard library installed.
# Make sure to  only use it
def createenv(parms, config):

    if "npm" in config:
        for dir in config["npm"]:
            with chdir(dir):
                system("npm ci")
