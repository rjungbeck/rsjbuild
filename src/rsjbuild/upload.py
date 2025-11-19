import pathlib

import logging

logger = logging.getLogger(__name__)

from .utils import system

def rename(renames, version):
    for target, source in renames.items:
        sourcePath = pathlib.Path(".") / source

        target = target.format(version=version, stem=sourcePath.stem, suffix=sourcePath.suffix, name=sourcePath.name)
        sourcePath.rename(target)

def upload(uploads, version, uploadPrefix):

    for target, source in uploads.items():

        for sourcePath in pathlib.Path(".").glob(source):
            if sourcePath.name == "":
                continue

            if sourcePath.is_file():
                targetStr = target.format(version=version, stem=sourcePath.stem, suffix=sourcePath.suffix, name=sourcePath.name, uploadPrefix=uploadPrefix)
                system(f"scp {str(sourcePath)} {targetStr}")
            else:
                targetStr = target.format(version=version, ustem=sourcePath.stem, suffix=sourcePath.suffix, name=sourcePath.name, ploadPrefix=uploadPrefix)
                system(f"scp -r {str(sourcePath)} {targetStr}")
