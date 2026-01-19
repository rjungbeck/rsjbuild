import subprocess
import json
import sys
import logging

logger = logging.getLogger(__name__)

def getVersion():
    try:
        result = subprocess.run(["git", "describe", "--tags"], capture_output=True, text=True)

        version = result.stdout
        print(f"Version from git: {version}")
        version = version.strip().replace("-", ".")
        versionPart = version.split(".")

        versionPart[0] = int(versionPart[0])
        versionPart[1] = int(versionPart[1])
        versionPart[2] = int(versionPart[2])
        version = f"{versionPart[0]:d}.{versionPart[1]:02d}.{versionPart[2]:04d}"
    except Exception:
        version = "0.00.00000"
    return version


def getCommit():
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return "0000000000000000000000000000000000000000"


def setVersion(targetPath, exeName=None):

    version = getVersion()
    commitHash = getCommit()

    versionPart = version.split(".")
    versionPart[0] = int(versionPart[0])
    versionPart[1] = int(versionPart[1])
    versionPart[2] = int(versionPart[2])
    versionPart.append(0)

    commaVersion = f"{versionPart[0]:d},{versionPart[1]:d},{versionPart[2]:d},0"
    pointVersion = f"{versionPart[0]:d}.{versionPart[1]:02d}.{versionPart[2]:04d}"

    versionPath = targetPath / "version.json"
    versionPath.write_text(json.dumps(version))

    versionPy = targetPath / "version.py"
    versionPy.write_text(f'version = "{version}"\n')
    versionPy.write_text(f'commitHash = "{commitHash}"\n')

    buildPath = targetPath / "build"
    buildPath.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        for rcTemplate  in targetPath.glob("*.rc"):
            resourceTemplate = rcTemplate.read_text()
            resource = resourceTemplate.replace("{{commaVersion}}", commaVersion)
            resource = resource.replace("{{pointVersion}}", pointVersion)
            resource = resource.replace("{{commitHash}}", commitHash)
            resourceFile = buildPath / rcTemplate.name
            resourceFile.write_text(resource)

    print(f"Building Version: {version}")

    return version
