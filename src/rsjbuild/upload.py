import pathlib

import logging

logger = logging.getLogger(__name__)


import fabric

def rename(renames, version):
    for target, source in renames.items:
        sourcePath = pathlib.Path(".") / source

        target = target.format(version=version, stem=sourcePath.stem, suffix=sourcePath.suffix, name=sourcePath.name)
        sourcePath.rename(target)

def upload(uploads, version):

    for target, source in uploads.items():
        (hostUrl, target) = target.split(":", 1)
        (user, host) = hostUrl.split("@", 1)

        with (fabric.Connection(host, user=user) as conn):
            for sourcePath in pathlib.Path(".").glob("*", recursive=True):
                if sourcePath.is_file():
                    target = target.format(version=version, stem=sourcePath.stem, suffix=sourcePath.suffix, name=sourcePath.name)
                    conn.put(str(sourcePath), target)
                else:
                    conn.put(str(sourcePath), target)
