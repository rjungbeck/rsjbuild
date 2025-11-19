import os
import subprocess
import hashlib
import base64
import datetime
import glob
import json
import pathlib
import contextlib
import shutil
import logging

logger = logging.getLogger(__file__)

import jwt
import addict
import boto3

def getCodesigningKey(privateKeyPath, privateKeyPassword):
    if "CODESIGNING_CERTIFICATE_BASE64" in os.environ:
        cs = os.environ["CODESIGNING_CERTIFICATE_BASE64"]
        cs = base64.b64decode(cs)
        privateKeyPath = pathlib.Path("build/codesigning.p12")
        privateKeyPath.write_bytes(cs)

    if "CODESIGNING_CERTIFICATE_KEY" in os.environ:
        privateKeyPassword = os.environ["CODESIGNING_CERTIFICATE_KEY"]

    return privateKeyPath, privateKeyPassword

def createInstaller(sourcePath, targetPath, title, version,  specialVersion=None, sign=False,  innoSetupPath="", signTool=[], codesigningKey=None, certificatePath=None, timestampUrl="", additionalParms={}):

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

        certificatePath = certificatePath.resolve()
        print("Certificate path: ", certificatePath)

        signToolFound = None
        for fileName in glob.glob(signTool):
            signToolFound = fileName
            print("Sign tool found: ", signToolFound)


        if signToolFound and certificatePath.exists():
            print("Signing installer")
            wrkPath = targetPath.parent

            with contextlib.chdir(wrkPath):

                digestPath = pathlib.Path("digest")
                digestPath.mkdir(parents=True, exist_ok=True)

                signTitle = title
                if specialVersion:
                    signTitle += " " + specialVersion

                # Create digest
                signParms=[
                    signToolFound,
                    "sign",
                    "/dg", str(digestPath),
                    "/fd", "SHA256",
                    "/du","https://www.rsj.de",
                    "/f", str(certificatePath),
                    "/d", signTitle,
                    targetPath.name,
                    ]

                subprocess.call(signParms)

                # Sign digest
                digestFilePath = digestPath / (targetPath.name + ".dig")

                digest = digestFilePath.read_text()
                digest = base64.b64decode(digest)

                kms = boto3.client("kms")

                rsp = kms.sign(KeyId=codesigningKey, Message=digest, MessageType="DIGEST", SigningAlgorithm="RSASSA_PKCS1_V1_5_SHA_256")
                signature = rsp["Signature"]
                signature = base64.b64encode(signature)

                signatureFilePath = digestPath / (digestFilePath.name + ".signed")
                signatureFilePath.write_bytes(signature)

                # Insert signature into installer
                signParms=[
                    signToolFound,
                    "sign",
                    "/di", str(digestPath),
                    targetPath.name
                    ]
                subprocess.call(signParms)

                shutil.rmtree(digestPath, ignore_errors=True)

                if timestampUrl:

                    # Timestamp
                    signParms=[
                        signToolFound,
                        "timestamp",
                        "/tr", timestampUrl,
                        "/td", "sha256",
                        targetPath.name
                        ]
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
