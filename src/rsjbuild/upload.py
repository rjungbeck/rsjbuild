import pathlib
import glob
import os
from contextlib import chdir
import logging

logger = logging.getLogger(__name__)


import fabric

def upload(uploadHost, uploadUser, version, mainModule, uploadTarget, additionalUploads):
    with  fabric.Connection(uploadHost, user=uploadUser) as conn:
        with conn.sftp() as sftp:
            sftp.put(f"output/{mainModule}Inst.exe", f"{uploadTarget}/{mainModule}Inst-{version}.exe")

            for additionalUpload in additionalUploads:
                source = additionalUpload[0]
                target = additionalUpload[1]

                if os.path.isdir(source):

                    with chdir(source):

                        for fileName in glob.glob("**", recursive=True):
                            p = pathlib.Path(fileName)
                            if p.is_file():
                                fileName = fileName.replace("\\", "/")
                                remoteName = f"{target}/{fileName}"
                                print(p.parent, p.name, remoteName)
                                sftp.put(fileName, remoteName)
                            else:

                                try:
                                    fileName = fileName.replace("\\", "/")
                                    sftp.mkdir(f"{target}/{fileName}")
                                except Exception:
                                    pass
                else:
                    sftp.put(source, target)