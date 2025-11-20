import base64
import sys
import shutil
import logging
import pathlib
import json
import os
import os.path
import zipfile
import gzip
import subprocess
from contextlib import chdir

from Cython.Compiler.ExprNodes import NoneNode

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

    for name, content in config.base64Decode.items():
        content = os.environ.get(content)
        if content:
            content = content.encode("utf-8")
            content = base64.b64decode(content)
            targetPath = basePath / name
            targetPath.write_bytes(content)
            print(f"Decoded {name}")

    version = getVersion()

    buildPath = basePath / "build"
    buildPath.mkdir(parents=True, exist_ok=True)

    outputPath = basePath / "output"
    outputPath.mkdir(parents=True, exist_ok=True)

    embedPath = basePath / "embed"
    embedPath.mkdir(parents=True, exist_ok=True)

    if parms.buildEmbed:
        createEmbedded(embedPath,
                       exeName=config.exeName,
                       createDirs=config.createDirs,
                       copyTrees=config.copyTrees,
                       copyFiles=config.copyFiles,
                       deleteFiles=config.deleteFiles,
                       compModules=config.compModules,
                       buildPath=buildPath,
                       includeTkinter=config.withTkinter,
                       removeTests=False)

    for secretEnv, files in config.template.items():
        if secretEnv in os.environ:
            secrets = os.environ[secretEnv]
            secrets = json.loads(secrets)

            for target, template in files.items():
                templatePath = basePath / template
                targetPath = embedPath / target
                text = templatePath.read_text()
                for secret, value in secrets.items():
                    text = text.replace(f"${{{secret}}}", value)
                targetPath.write_text(text)

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

    if pathlib.Path("locale").exists():
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

    if "pnpm" in config:
        for directory in config.pnpm:
            with chdir(directory):
                os.environ["NODE_OPTIONS"] = "--max-old-space-size=8192"
                system("pnpm i")
                system("pnpm run build")

    pathlib.Path("buildout").mkdir(exist_ok=True, parents=True)
    pathlib.Path("buildcss").mkdir(exist_ok=True, parents=True)

    if "require" in config:

        for source, prepare in config.require.items():
            pythonCall(prepare)
            with chdir(source):
                system("pnpm i")
                system("pnpm run build")

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

                certificatePath = None
                if "certificatePath" in config:
                    certificatePath = pathlib.Path(config.certificatePath)

                codesigningKey = None
                if "codesigningKey" in config:
                    codesigningKey = config.codesigningKey

                createInstaller(installerSourcePath,
                                installerPath,
                                options.title,
                                version,
                                sign=parms.sign,
                                innoSetupPath=pathlib.Path(config.innoSetupPath),
                                signTool=config.signTool,
                                codesigningKey=codesigningKey,
                                certificatePath =certificatePath,
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
                            # print(f"Adding {str(filePath)} as {targetName}")
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
                                # print(f"Adding {str(filePath)} as {targetName}")
                                zip.write(filePath, targetName)

                        for dirName in extra.dirList:
                            dirPath = pathlib.Path(dirName)
                            for filePath in dirPath.glob("**/*"):
                                if filePath.is_file():
                                    targetName = str(prefixPath / filePath)
                                    if targetName not in included:
                                        included.add(targetName)
                                        # print(f"Adding {str(filePath)} as {targetName}")
                                        zip.write(filePath, targetName)

                doCopy(options.post)

    if parms.withUnzip:
        for (output, source) in config.unzip:
            outputPath = pathlib.Path(output)
            shutil.rmtree(outputPath, ignore_errors=True)
            outputPath.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(source) as zipFile:
                for member in zipFile.infolist():
                    extracted_path = zipFile.extract(member, outputPath)

                    # Restore file permissions (including execute) if created on Unix
                    if member.create_system == 3:
                        unix_mode = member.external_attr >> 16
                        if unix_mode:
                            os.chmod(extracted_path, unix_mode)

    if parms.upload:

        if parms.publish:

            for installer, options in config.installers.items():

                installerPath = pathlib.Path("output") / installer
                versionPath = pathlib.Path("output") / options.currentVersion

                publishInstaller(installerPath,
                                 version,
                                 downloadUrl=options.downloadUrl,
                                 installArgs=config.installArgs,
                                 updateInterval=config.updateInterval,
                                 keytoolConfigPath=basePath / "keytool.json",
                                 versionPath=versionPath)

        if config.uploadHost and config.uploadHost != "$(UPLOAD_HOST}" and config.uploadHost != " " :
            upload(config.upload, version, config.uploadPrefix)
