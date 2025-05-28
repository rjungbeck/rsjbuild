import sys
import os
import subprocess


def nodeCall(pgm, nodeArgs, cwd=None,package=""):
    if sys.platform=="win32":
        nodeCmd="c:/Program Files/nodejs/npx.cmd"
        nodePath="c:/Program Files/nodejs/node_modules/"+package+"/bin"
        nodePath=os.path.join(os.getenv("APPDATA"), "npm", "node_modules", package, "bin")
        nodePath = ""
    elif sys.platform=="darwin":
        nodeCmd="/usr/local/bin/npx"
        nodePath="/usr/local/lib/node_modules/"+package+"/bin"
    else:
        nodeCmd="npx"
        nodePath="/usr/local/bin/"

    nodePgm=os.path.join(nodePath, pgm)

    if sys.platform=="win32":
        commandLine='"%s" "%s" %s' % (nodeCmd, nodePgm, nodeArgs)
        commandLine=commandLine.replace("/","\\")
    else:
        commandLine='%s %s %s' % (nodeCmd, nodePgm, nodeArgs)

    print("SubProcess: ", commandLine)
    subprocess.call(commandLine, cwd=cwd, shell=True)

def requireCall (requireArgs, cwd="."):
    if sys.platform =="win32":
        requirePgm = "r.js.cmd"
    else:
        requirePgm = "r.js"
    nodeCall(requirePgm, requireArgs, cwd=cwd, package="requirejs")
