import pathlib
import sysconfig
import shutil
import sys
import urllib.request
import zipfile
import logging
import py_compile
import os

logger = logging.getLogger(__file__)

from .utils import copytree, system

def getEmbeddedDistribution():
    pythonVersion = sys.version_info
    pythonVersionName = f"{pythonVersion.major}.{pythonVersion.minor}.{pythonVersion.micro}"

    distributionName = f"python-{pythonVersionName}-embed-amd64.zip"
    distributionPath = pathlib.Path("./build") / distributionName
    if not distributionPath.exists():
        downloadUrl = f"https://www.python.org/ftp/python/{pythonVersionName}/{distributionName}"
        print(downloadUrl)
        urllib.request.urlretrieve(downloadUrl, filename=distributionPath)
    return distributionPath

def getLicenseText(target, targetPath, *args):
    with target.open("wb") as combinedFile:

        for arg in args:
            licenseTxt = arg.read_bytes()
            combinedFile.write(licenseTxt)

        for licensePath in targetPath.rglob("[lL][iI][cC][eE][nN][sS][eE]*"):
            if licensePath.is_file():
                try:
                    print(licensePath)
                    libraryPath = licensePath.relative_to(targetPath).parents[-2]
                    libraryNameComponents = libraryPath.name.split("-")
                    libraryName = libraryNameComponents[0]
                    combinedFile.write(f"\n**********************\nLicense for {libraryName} ({str(licensePath)})\n\n".encode("utf-8"))
                    licenseTxt = licensePath.read_bytes()
                    combinedFile.write(licenseTxt)
                except Exception:

                   pass

def doCopyFiles(targetPath, sourcePath, createDirs=[], copyFiles=[], copyTrees=[], deleteFiles=[]):

    if createDirs:
        for dir in createDirs:
            newDir = targetPath / dir
            newDir.mkdir(parents=True, exist_ok=True)

    if copyFiles:
        for fileName in copyFiles:
            try:
                if isinstance(fileName, str):
                    (targetPath / fileName).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(sourcePath / fileName, targetPath / fileName)
                else:
                    (targetPath / fileName[1]).parent.mkdir(parents=True, exist_ok=True)
                    if fileName[0].startswith("https://") or fileName[0].startswith("http://"):
                        urllib.request.urlretrieve(fileName[0], filename=targetPath / fileName[1])
                    else:
                        shutil.copy2(sourcePath / fileName[0], targetPath / fileName[1])
            except Exception:
                logger.exception(fileName)

    if copyTrees:
        for tree in copyTrees:
            if isinstance(tree, str):
                wrkPath = sourcePath / tree
                (targetPath /tree).mkdir(parents=True, exist_ok=True)
                shutil.copytree(wrkPath, targetPath / tree, dirs_exist_ok=True)
            else:
                wrkPath = sourcePath / tree[0]
                (targetPath / tree[1]).mkdir(parents=True, exist_ok=True)
                shutil.copytree(wrkPath, targetPath / tree[1], dirs_exist_ok=True)

    if deleteFiles:
        for fileName in deleteFiles:
            try:
                (targetPath / fileName).unlink()
            except Exception:
                pass


def createEmbedded(targetPath, exeName="main", buildPath=None, createDirs=[], copyFiles=[], copyTrees=[], deleteFiles=[], compModules=[],
                   includeTkinter=False, removeTests=True):

    vars = sysconfig.get_config_vars()
    pPath = vars['installed_platbase']
    pPath = pathlib.Path(pPath)

    shutil.rmtree(targetPath, ignore_errors=True)

    pythonVersion = sys.version_info
    #pythonVersionName = f"{pythonVersion.major}.{pythonVersion.minor}.{pythonVersion.micro}"
    pythonVersionNameShort = f"{pythonVersion.major}.{pythonVersion.minor}"

    if sys.platform == "win32":
        targetPath.mkdir(parents=True)

        distributionPath = getEmbeddedDistribution()

        with zipfile.ZipFile(distributionPath) as zipFile:
            zipFile.extractall(path=targetPath)
    else:
        system(f"uv venv --python {pythonVersionNameShort} {str(targetPath)}")

    system("uv export --no-dev --output-file build/requirements.txt")
    if sys.platform == "win32":
        system(f"uv pip install --upgrade --no-deps --target {str(targetPath)} -r build/requirements.txt")
    else:
        os.environ["VIRTUAL_ENV"] = str(targetPath)
        system("uv pip install --upgrade --no-deps -r build/requirements.txt")
        del os.environ["VIRTUAL_ENV"]

    doCopyFiles(targetPath, pathlib.Path("."), createDirs=createDirs, copyFiles=copyFiles, copyTrees=copyTrees)

    getLicenseText(targetPath / "license.txt", targetPath, targetPath / "../install/license.txt")

    if sys.platform == "win32":

        pth = f"{exeName}\n{exeName}.exe\n.\nlib\nlib/site-packaqges\nimport site\n"
        pthName = f"python{pythonVersion.major}{pythonVersion.minor}._pth"
        (targetPath / pthName).write_text(pth)

        if includeTkinter:

            shutil.copytree(pPath / "tcl", targetPath / "tcl")
            shutil.copytree(pPath / "lib/tkinter", targetPath / "tkinter")
            copytree(pPath / "dlls", targetPath)

        if removeTests:
            for path in targetPath.rglob("[tT][eE][sS][tT][sS]"):
                print(f"Deleting {path}")
                shutil.rmtree(path, ignore_errors=True)

        pythonLibraryName = f"python{pythonVersion.major}{pythonVersion.minor}.zip"

        pythonLib = targetPath / pythonLibraryName

        if pythonLib.exists():
            libraryPath = buildPath / "library.zip"
            shutil.copy(pythonLib, libraryPath)
            pythonLib.unlink()
            libraryMode = "a"
        else:
            libraryPath = buildPath / "library.zip"
            libraryMode = "w"

        with zipfile.ZipFile(str(libraryPath), libraryMode) as zipFile:

            for modName in compModules:
                try:
                    modPath = targetPath / modName
                    for srcPath in modPath.rglob("*.py"):
                        compPath = srcPath.with_suffix(".pyc")
                        try:
                            py_compile.compile(str(srcPath), cfile=str(compPath), optimize=2, doraise=True)
                        except Exception:
                            compPath = srcPath

                        arcPath = pathlib.PurePosixPath(modName) / compPath.relative_to(modPath)
                        zipFile.write(compPath, arcname=str(arcPath))

                    shutil.rmtree(modPath, ignore_errors=True)
                except Exception:
                    logger.exception(f"Compressing module {modName}")

        for distPath in targetPath.glob("*.dist-info"):
            print(f"Deleting {distPath}")
            shutil.rmtree(distPath, ignore_errors=True)

        for eggPath in targetPath.glob("*.egg-info"):
            print(f"Deleting {eggPath}")
            shutil.rmtree(eggPath, ignore_errors=True)

        shutil.rmtree(targetPath / "bin", ignore_errors=True)
        shutil.rmtree(targetPath / "__pycache__", ignore_errors=True)

    doCopyFiles(targetPath, pathlib.Path("."), deleteFiles=deleteFiles)

