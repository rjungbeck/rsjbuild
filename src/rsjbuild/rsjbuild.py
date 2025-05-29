import argparse
import os.path
import logging
import pathlib
import json

logger = logging.getLogger("rsjbuild")

from .rsjbuildversion import version as rsjbuildVersion

def main():

    global rsjbuildVersion

    parser = argparse.ArgumentParser(description="Portfolio Frontend Build",
                                     epilog="(C) Copyright 2022-2025 by RSJ Software GmbH Germering. All rights reserved.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     prog="rsjbuild")
    parser.add_argument("--version", action="version", version=f"%(prog)s  {rsjbuildVersion}", help="Display version")
    parser.add_argument("--config", type=pathlib.Path, default="build.json", help="Configuration file")

    subparsers = parser.add_subparsers(title="Commands", dest="command")

    initParser = subparsers.add_parser("init", help="Initialize build directory")
    initParser.set_defaults(func=doInit)

    buildParser = subparsers.add_parser("build", help="Build portfolio frontend")

    buildParser.add_argument("--force", action="store_true", help="Force recompile")
    buildParser.add_argument("--buildEmbed", action="store_true", help="Build embed directory")
    buildParser.add_argument("--withInstaller", action="store_true", help="Generate installer")
    buildParser.add_argument("--withZip", action="store_true", help="Generate zip distribution")
    buildParser.add_argument("--withUnzip", action="store_true", help="Unzip distribution")
    buildParser.add_argument("--sign", action="store_true", help="Sign installer")
    buildParser.add_argument("--upload", action="store_true", help="Upload installer")
    buildParser.add_argument("--noConsole", action="store_true", help="Do not show console in executable")
    buildParser.add_argument("--publish", action="store_true", help="Publish")
    buildParser.set_defaults(func=doBuild)

    keytoolParser = subparsers.add_parser("keytool", help="Keytool")
    keytoolParser.add_argument("--keyConfig", type=pathlib.Path, default="keytool.json", help="Configuration file")
    keytoolParser.add_argument("--expiration", type=int, default=None, help="Expiration time in days")
    keytoolParser.add_argument("--expirationMinutes", type=int, default=None, help="Expiration time in minutes")
    keytoolParser.add_argument("--licensee", type=str, default="RSJ Software GmbH", help="Licensee")
    keytoolParser.add_argument("--email", type=str, default=None, help="Licensee Email")
    keytoolParser.add_argument("--min", type=str, default=None, help="Min Version")
    keytoolParser.add_argument("--max", type=str, default=None, help="Max Version")
    keytoolParser.add_argument("--template", type=pathlib.Path, default=None, help="Template file")
    keytoolParser.add_argument("--demo", action="store_false", help="Demo key")
    keytoolParser.add_argument("output", type=pathlib.Path, help="Output file")
    keytoolParser.set_defaults(func=doKeytool)

    versionParser = subparsers.add_parser("version", help="Display version")
    versionParser.set_defaults(func=doVersion)

    parms = parser.parse_args()
    userConfigText = parms.config.read_text()
    userConfigText = os.path.expandvars(userConfigText)
    userConfig = json.loads(userConfigText)

    rsjbuildPath = pathlib.Path(__file__).parent.resolve()
    defaultPath = rsjbuildPath / "default.json"

    defaultConfigText = defaultPath.read_text()
    defaultConfigText = os.path.expandvars(defaultConfigText)
    defaultConfig = json.loads(defaultConfigText)

    config = merge(userConfig, defaultConfig)

    parms.func(parms, config)


def merge(source, destination):
    """
    run me with nosetests --with-doctest file.py

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value

    return destination

def doInit(parms, config):
    from .createenv import createenv
    createenv(parms, config)

def doBuild(parms, config):

    from .build import build
    build(parms, config)

def doKeytool(parms, config):

    from .keytool import keytool
    keytool(parms, config)

def doVersion(parms, config):
    print(rsjbuildVersion)


if __name__ == "__main__":
    main()
