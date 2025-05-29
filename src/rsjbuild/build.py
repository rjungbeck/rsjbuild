import sys
import shutil
import logging
import pathlib
import json
import os
import zipfile
import gzip
import subprocess
from contextlib import chdir

logger = logging.getLogger(__file__)

import addict

from .getversion import getVersion, setVersion
from .embedded import createEmbedded, doCopyFiles
from .installer import createInstaller, publishInstaller
from .compile import compile
from .language import procMessages
from .upload import upload
from .utils import pythonCall

def system(cmd):
    print(cmd)
    subprocess.run(cmd, shell=True, check=True)

def doCopy(options):
    if options:
        createDirs = options.get("createDirs", [])
        copyFiles = options.get("copyFiles", [])
        copyTrees = options.get("copyTrees", [])
        deleteFiles = options.get("deleteFiles", [])

        doCopyFiles(pathlib.Path("embed"), pathlib.Path("."), createDirs=createDirs, copyFiles=copyFiles, copyTrees=copyTrees, deleteFiles=deleteFiles)

def inPatternList(filePath, ignoreList):
    for ignorePattern in ignoreList:
        if filePath.match(ignorePattern):
            return True
    return False

def build(parms, config):

    config = addict.Dict(config)

    basePath = pathlib.Path(".")

    version = getVersion()

    buildPath = basePath / "build"
    buildPath.mkdir(parents=True, exist_ok=True)

    outputPath = pathlib.Path("output")
    outputPath.mkdir(parents=True, exist_ok=True)

    if parms.buildEmbed:
        createEmbedded(basePath / "embed",
                       exeName=config.exeName,
                       createDirs=config.createDirs,
                       copyTrees=config.copyTrees,
                       copyFiles=config.copyFiles,
                       deleteFiles=config.deleteFiles,
                       compModules=config.compModules,
                       buildPath=buildPath,
                       includeTkinter=config.withTkinter,
                       removeTests=False)

    sourcePath = basePath / config.sourcePath

    setVersion(sourcePath, config.exeName)

    if "embedData" in config:
        for (k, v) in config.embedData.items():
            target = sourcePath / k
            sourceData = pathlib.Path(v)

            data = json.loads(sourceData.read_text())
            data = f"{target.stem} = {json.dumps(data, indent=2)}\n"

            target.write_text(data)

    for exeName, compileArgs in config.compile.items():

        if "onlyOn" in compileArgs:
            if sys.platform not in compileArgs.onlyOn:
                continue

        exePath = compile(sourcePath,
                          exeName,
                          compileArgs.mainModule,
                          compileArgs.sources,
                          noConsole=compileArgs.noConsole,
                          force=parms.force)

        embedPath = pathlib.Path("embed")

        if sys.platform == "win32":
            binPath = embedPath
            shutil.copy(exePath, embedPath)
        else:
            binPath = embedPath / "bin"

        binPath.mkdir(parents=True, exist_ok=True)
        shutil.copy(exePath, binPath)

    procMessages(config.sourcePath, config.exeName)
    pathlib.Path("embed/locale").mkdir(parents=True, exist_ok=True)
    shutil.copytree("locale", "embed/locale", ignore=shutil.ignore_patterns("*.po"), dirs_exist_ok=True)

    if "userguide" in config:

        pythonPath = pathlib.Path(sys.executable).parent

        mkDocs = str(pythonPath / "mkdocs")

        userguidePath = pathlib.Path(config.userguide)
        targetPath = pathlib.Path("embed") / config.userguide

        for dir in userguidePath.glob("*"):
            with chdir(dir):
                system(f"{mkDocs} build")

            targetDirPath = targetPath / dir.name
            targetDirPath.mkdir(parents=True, exist_ok=True)
            shutil.copytree(dir / "site", targetDirPath / "site", dirs_exist_ok=True)

    if "npm" in config:
        for directory in config.npm:
            with chdir(directory):
                os.environ["NODE_OPTIONS"] = "--max-old-space-size=8192"
                system("npm ci")
                system("npm run build")

    pathlib.Path("buildout").mkdir(exist_ok=True, parents=True)
    pathlib.Path("buildcss").mkdir(exist_ok=True, parents=True)

    if "require" in config:

        for source, prepare in config.require.items():
            pythonCall(prepare)
            with chdir(source):
                system("npm ci")
                system("npm run build")

    if "gzip" in config:
        for source in config.gzip:
            sourcePath = pathlib.Path(source)

            for filePath in sourcePath.glob("**/*"):
                if filePath.is_file():
                    if filePath.suffix in [".gz", ".zip", ".png", ".gif", ".jpg", ".jpeg"]:
                        continue

                    with gzip.open(str(filePath)+".gz", "wb") as gzipFile:
                        with filePath.open("rb") as file:
                            shutil.copyfileobj(file, gzipFile)

    doCopy(config.lateCopy)

    if parms.withInstaller:

        if sys.platform == "win32":
            installerSourceDirPath = pathlib.Path("install")
            installerOutputDirPath = pathlib.Path("output")

            for (output, options) in config.installers.items():

                doCopy(options.pre)

                installerSourcePath = installerSourceDirPath / options.source
                installerPath = installerOutputDirPath / output

                privateKeyPath = None
                privateKeyPassword = None

                if "privateKeyPath" in config:
                    privateKeyPath = pathlib.Path(config.privateKeyPath)

                if "privateKeyPassword" in config:
                    privateKeyPassword = config.privateKeyPassword

                createInstaller(installerSourcePath,
                                installerPath,
                                options.title,
                                version,
                                sign=parms.sign,
                                innoSetupPath=pathlib.Path(config.innoSetupPath),
                                signTool=config.signTool,
                                privateKeyPath=privateKeyPath,
                                privateKeyPassword=privateKeyPassword,
                                timestampUrl=config.timestampUrl,
                                additionalParms=options.get("additionalParms", {}))

                doCopy(options.post)

    if parms.withZip:
        print("Creating zip files")
        if sys.platform == "linux":

            for (output, options) in config.zips.items():

                doCopy(options.pre)

                prefixPath = pathlib.Path(config.exeName)
                zipPath = pathlib.Path("output") / output
                embedPath = pathlib.Path("embed")

                included = set()

                print(f"Creating zip file {str(zipPath)}")

                with zipfile.ZipFile(zipPath, "w", compression=zipfile.ZIP_DEFLATED) as zip:
                    ignoreList = options.get("ignore", [])

                    for filePath in embedPath.glob("**/*"):
                        relFilePath = filePath.relative_to(embedPath)
                        if inPatternList(relFilePath, ignoreList):
                            continue

                        for ignorePattern in ignoreList:
                            relFilePath.full_match(ignorePattern)
                            continue
                        if filePath.is_file():
                            targetName = str(prefixPath / relFilePath)
                            print(f"Adding {str(filePath)} as {targetName}")
                            included.add(targetName)
                            zip.write(filePath, targetName)

                    if "extra" in options:
                        extra = json.loads(pathlib.Path(options.extra).read_text())
                        extra = addict.Dict(extra)

                        for fileName in extra.fileList:
                            filePath = pathlib.Path(fileName)
                            targetName = str(prefixPath / filePath)
                            if targetName not in included:
                                included.add(targetName)
                                print(f"Adding {str(filePath)} as {targetName}")
                                zip.write(filePath, targetName)

                        for dirName in extra.dirList:
                            dirPath = pathlib.Path(dirName)
                            for filePath in dirPath.glob("**/*"):
                                if filePath.is_file():
                                    targetName = str(prefixPath / filePath)
                                    if targetName not in included:
                                        included.add(targetName)
                                        print(f"Adding {str(filePath)} as {targetName}")
                                        zip.write(filePath, targetName)

                doCopy(options.post)

    if parms.withUnzip:
        for (output, source) in config.unzip:
            outputPath = pathlib.Path(output)
            shutil.rmtree(outputPath, ignore_errors=True)
            outputPath.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(source) as zipFile:
                zipFile.extractall(outputPath)

    if parms.upload:

        if parms.publish:
            installerPath = pathlib.Path("output") / f"{config.exeName}Inst.exe"

            publishInstaller(installerPath, version,
                             downloadUrl=config.downloadUrl,
                             installArgs=config.installArgs,
                             updateInterval=config.updateInterval,
                             keytoolConfigPath=basePath / "keytool.json")


        upload(config.upload, version)
