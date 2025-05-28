import sys
import pathlib
import sysconfig
import stat
import collections
import logging

logger = logging.getLogger(__file__)

from setuptools._distutils.ccompiler import new_compiler

from .utils import pythonCall, template

rsjbuildPath = pathlib.Path(__file__).parent.resolve()


def getCompiler(noInit=False):

    compiler = new_compiler()
    compiler.define_macro("NDEBUG")
    #compiler.define_macro("CYTHON_PEP489_MULTI_PHASE_INIT", 0)
    if noInit:
        compiler.define_macro("CYTHON_NO_PYINIT_EXPORT", 1)

    compiler.add_include_dir(sysconfig.get_path("include"))

    configVars = sysconfig.get_config_vars()
    compiler.add_library_dir(configVars.get("installed_platbase") + "/libs")

    if sys.platform == "linux":
        compiler.add_library_dir(configVars.get("LIBM"))
        compiler.add_library_dir(configVars.get("LIBPL"))
        compiler.add_library_dir(configVars.get("LIBDIR"))

        compiler.add_library("m")

        compiler.add_library(configVars.get("LIBRARY")[3:-2])
        for lib in configVars.get("LIBS").split():
            compiler.add_library(lib[2:])

        compiler.add_library("z")

    return compiler

def compile(sourcePath, exeName, mainModule, sources, force=True, noConsole=False, library=False, noInit=False):

    targetPath = pathlib.Path("build")

    buildPath = (sourcePath / "build")
    buildPath.mkdir(parents=True, exist_ok=True)

    cSources = []
    objects = []
    pySources = []

    modules = []

    packageModules = collections.defaultdict(list)
    qualifiedModules = []

    if sys.platform == "win32":
        objSuffix = ".obj"
        exeSuffix = ".exe"

        rcPath = (buildPath / exeName).with_suffix(".rc")
        if rcPath.exists():
            cSources.append(rcPath)
    else:
        objSuffix = ".o"
        exeSuffix = ""

    sourceSet = set()
    for source in sources:
        sourceSet.update(list(sourcePath.glob(source)))
    sources = sorted(list(sourceSet))


    for filePath in sources:
        modName = filePath.stem
        if modName != "__init__":
            if filePath.parent == sourcePath:
                package = ""
            else:
                package = filePath.parent.stem
            objPath = (buildPath / modName).with_suffix(objSuffix)
        else:
            continue

        dirty = True
        if not force:
            if objPath.exists():
                if objPath.stat().st_mtime > filePath.stat().st_mtime:
                    dirty = False

        packageModules[package].append(modName)
        modules.append(modName)

        if package:
            qualifiedModules.append(f"{package}.{modName}")
        else:
            qualifiedModules.append(modName)

        if dirty:
            pySources.append(filePath)
            cSources.append((buildPath / modName).with_suffix(".c"))
        else:
            objects.append(objPath)

    packages = list(filter(lambda x: len(x) > 0, packageModules.keys()))

    template(rsjbuildPath / "bootstrap.pyx",
             buildPath / "bootstrap.pyx",
             modules=packageModules[""] + packages,
             package="__main__",
             packages=packages,
             qualifiedModules=qualifiedModules,
             mainModule=mainModule,
             debug=False)

    template(rsjbuildPath / "bootstrap.h",
             buildPath / "__main__.h",
             modules=packageModules[""],
             packages=packages)

    pythonCall(f'-m cython -3 --embed --no-docstrings {str(buildPath / "bootstrap.pyx")}')
    cSources.append(buildPath / "bootstrap.c")

    for package in packages:
        template(rsjbuildPath / "bootstrap.pyx",
                 buildPath / f"{package}.pyx",
                 modules=packageModules[package],
                 package=package,
                 qualifiedModules=qualifiedModules,
                 packages=[],
                 debug=False)
        template(rsjbuildPath / "bootstrap.h",
                 buildPath / f"{package}.h",
                 modules=packageModules[package],
                 package=package,
                 packages=[])

        pySources.append((buildPath / package).with_suffix(".pyx"))

        cSources.append((buildPath / package).with_suffix(".c"))

    if len(pySources):
        pySources = list(map(str, pySources))

        rest = pySources

        while len(rest):

            pythonCall(f"-m cython -3 --no-docstrings --output-file {str(buildPath)} {' '.join(rest[:20])}")
        
            rest = rest[20:]

    cSourcesRel = []

    for cSource in cSources:
        try:
            cSourcesRel.append(str(cSource))
        except Exception:
            print("Problem resolving", cSource)
    compileArgs = []
    if library:
        if sys.platform == "linux":
            compileArgs = ["-fPIC"]

    print("cSources", cSourcesRel)

    compiledObjects  = getCompiler(noInit=True).compile(cSourcesRel,  extra_postargs=compileArgs)

    for compileObject in compiledObjects:
        if sys.platform == "linux":
            objects.append(pathlib.Path( compileObject))
        else:
            objects.append(pathlib.Path(compileObject))

    if sys.platform =="win32":
        objects += ["kernel32.lib", "ucrt.lib", "vcruntime.lib"]

    objects = list(map(str, objects))
    print("Objects", objects)

    linkerArgs = []

    outputName = exeName

    if sys.platform == "win32":
        outputName = "tmp"

        if noConsole:
            linkerArgs = ["/subsystem:windows", "/entry:wmainCRTStartup"]

    if sys.platform == "linux":
        configVars = sysconfig.get_config_vars()

        linkForShared = configVars.get("LINKFORSHARED")
        linkForShared = linkForShared.split(" ")
        linkerArgs = linkForShared + ["--no-pie", "-Xlinker", "--copy-dt-needed-entries"]

        pythonVersion = sys.version_info
        pythonMainVersion = f"{pythonVersion.major}.{pythonVersion.minor}"
        # /usr/lib/python3.11/config-3.11-x86_64-linux-gnu/libpython3.11-pic.a
        objects = [f"/usr/lib/python{pythonMainVersion}/config-{pythonMainVersion}-x86_64-linux-gnu/libpython{pythonMainVersion}-pic.a"] + objects

    getCompiler().link_executable(objects, outputName, output_dir="build", extra_preargs=linkerArgs)

    exePath = (targetPath / exeName).with_suffix(exeSuffix)

    if sys.platform == "win32":
        with exePath.open("wb") as f:
            tmpPath = (targetPath / "tmp").with_suffix(exeSuffix)
            exeBytes = tmpPath.read_bytes()
            f.write(exeBytes)

            zipLib = targetPath / "library.zip"
            zipBytes = zipLib.read_bytes()
            f.write(zipBytes)

        if sys.platform != "win32":
            exePath.chmod(exePath.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH | stat.S_IXUSR)

    return exePath


