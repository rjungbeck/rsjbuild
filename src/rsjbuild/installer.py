import os
import subprocess
import hashlib
import base64
import datetime
import glob
import json
import pathlib
import logging

logger = logging.getLogger(__file__)

import jwt
import addict

def getCodesigningKey(privateKeyPath, privateKeyPassword):
    if "CODESIGNING_CERTIFICATE_BASE64" in os.environ:
        cs = os.environ["CODESIGNING_CERTIFICATE_BASE64"]
        cs = base64.b64decode(cs)
        privateKeyPath = pathlib.Path("build/codesigning.p12")
        privateKeyPath.write_bytes(cs)

    if "CODESIGNING_CERTIFICATE_KEY" in os.environ:
        privateKeyPassword = os.environ["CODESIGNING_CERTIFICATE_KEY"]

    return privateKeyPath, privateKeyPassword

def createInstaller(sourcePath, targetPath, title, version,  specialVersion=None, sign=False,  innoSetupPath="", signTool=[], privateKeyPath=None, privateKeyPassword="", timestampUrl="", additionalParms={}):

    version = version.split(".")
    version = ".".join(version[:3])

    installerCall = [str(innoSetupPath),
                    "-dversion="+version,
                    "-doutputName="+targetPath.stem,
                    f"-O{str(targetPath.parent)}"]

    for define, value in additionalParms.items():
        installerCall.append(f"-d{define}={value}")

    installerCall.append(str(sourcePath))

    # Inno Setup
    subprocess.call(installerCall)

    # Sign
    if sign:

        privateKeyPath, privateKeyPassword = getCodesigningKey(privateKeyPath, privateKeyPassword)

        if privateKeyPath and privateKeyPassword and privateKeyPath.exists():

            signTitle=title

            if specialVersion:
                signTitle += " " + specialVersion

            signToolFound = None
            for fileName in glob.glob(signTool):
                signToolFound = fileName
                break

            signParms=[
                    signToolFound,
                    "sign",
                    "/n","RSJ Software GmbH",
                    "/f",str(privateKeyPath),
                    "/p",privateKeyPassword,
                    "/fd", "SHA256",
                    "/du","https://www.rsj.de",
                    "/d", signTitle,
                    "/t", timestampUrl,
                    str(targetPath)]

            subprocess.call(signParms)

        return targetPath

def publishInstaller(target, version, downloadUrl="", installArgs=[], updateInterval=86400, keytoolConfigPath=None, versionPath=None):
        with target.open( "rb") as installerFile:
            digest = hashlib.file_digest(installerFile, "sha512")

        hash = digest.hexdigest()

        version = version.split(".")
        version = ".".join(version[:3])

        currentVersion = {
            "version": version,
            "url": downloadUrl.format(version=version),
            "args": installArgs,
            "interval": updateInterval,
            "hash": hash
            }

        jsonPath = versionPath.with_suffix(".json")
        jsonPath.write_text(json.dumps(currentVersion))

        if "KEYTOOL_CONFIG" in os.environ:
            keytoolConfig = os.environ["KEYTOOL_CONFIG"]
        else:
            keytoolConfig = keytoolConfigPath.read_text()

        keytoolConfig = json.loads(keytoolConfig)
        keytoolConfig = addict.Dict(keytoolConfig)

        now = datetime.datetime.now(datetime.UTC)

        payload = {
            "iss": keytoolConfig.keytool.iss,
            "sub": f"build {version}",
            "aud": f"{keytoolConfig.keytool.aud} Update",
            "iat": now,
            "nbf": now,
            }

        payload |= currentVersion
        jwtToken = jwt.encode(payload, keytoolConfig.keytool.key, algorithm="ES256")

        jwtPath = versionPath.with_suffix(".jwt")
        jwtPath.write_text(jwtToken)
