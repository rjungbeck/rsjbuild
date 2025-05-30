import pathlib

import logging

logger = logging.getLogger(__name__)

from .utils import system

def rename(renames, version):
    for target, source in renames.items:
        sourcePath = pathlib.Path(".") / source

        target = target.format(version=version, stem=sourcePath.stem, suffix=sourcePath.suffix, name=sourcePath.name)
        sourcePath.rename(target)

def upload(uploads, version):

    for target, source in uploads.items():

        for sourcePath in pathlib.Path(".").glob(source):
            if sourcePath.filename == "":
                continue

            if sourcePath.is_file():
                target = target.format(version=version, stem=sourcePath.stem, suffix=sourcePath.suffix, name=sourcePath.name)
                system(f"scp -o StrictHostKeyChecking=no {str(sourcePath)} {target}")
            else:
                target = target.format(version=version)
                system(f"scp -r -o StrictHostKeyChecking=no {str(sourcePath)} {target}")
