import argparse
import os
import json
import datetime
import pathlib
import logging
logger = logging.getLogger(__file__)

import addict
import jwt

from .version import version

def main():

    parser = argparse.ArgumentParser(description="Key Tool",
                                     epilog="(C) Copyright 2022 by RSJ Software GmbH Germering. All rights reserved",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--keyConfig", type=pathlib.Path, default="keytool.json", help="Configuration file")
    parser.add_argument("--expiration", type=int, default=None, help="Expiration time in days")
    parser.add_argument("--expirationMinutes", type=int, default=None, help="Expiration time in minutes")
    parser.add_argument("--licensee", type=str, default="RSJ Software GmbH", help="Licensee")
    parser.add_argument("--email", type=str, default=None, help="Licensee Email")
    parser.add_argument("--min", type=str, default=None, help="Min Version")
    parser.add_argument("--max", type=str, default=None, help="Max Version")
    parser.add_argument("--template", type=pathlib.Path, default=None, help="Template file")
    parser.add_argument("--demo", action="store_false", help="Demo key")
    parser.add_argument("output", type=pathlib.Path, help="Output file")

    parms = parser.parse_args()

    keytool(parms, None)

def keytool(parms, config):

    if "KEYTOOL_CONFIG" in os.environ:
        keyConfig = os.environ["KEYTOOL_CONFIG"]
    else:
        keyConfig = parms.keyConfig.read_text()

    keyConfig = json.loads(keyConfig)
    keyConfig = addict.Dict(keyConfig)
    keyConfig["configFile"] = str(parms.keyConfig)

    now = datetime.datetime.now(datetime.UTC)
    payload = {
        "iss": keyConfig.keytool.iss,
        "sub": f"keytool {version}",
        "aud": keyConfig.keytool.aud,
        "iat": now,
        "nbf": now,
        "licensed": parms.demo
        }

    if parms.min:
        payload["minVersion"] = parms.min

    if parms.max:
        payload["maxVersion"] = parms.max

    if parms.licensee is not None:
        payload["licensee"] = parms.licensee

    if parms.email is not None:
        payload["email"] = parms.email

    if parms.expiration is not None:
        payload["exp"] = now + datetime.timedelta(days=parms.expiration)

    if parms.expirationMinutes is not None:
        payload["exp"] = now + datetime.timedelta(minutes=parms.expirationMinutes)

    if parms.template is not None:
        template = json.loads(parms.template.read_text())
        payload = payload | template

    jwToken = jwt.encode(payload, keyConfig.keytool.key, algorithm="ES256")
    print(jwToken)

    print(jwt.decode(jwToken, keyConfig.keytool.public, algorithms=["ES256"], audience=[keyConfig.keytool.aud], issuer=keyConfig.keytool.iss))

    parms.output.write_text(jwToken)

if __name__ == "__main__":
    main()