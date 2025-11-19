# RSJ Internal Build Tool

This tool is currently only useful for RSJ projects. It brings toegther different technologies used to build software diistributions:
* Cross platform builds
* Github Actions support
* Cython based Compilation
* PNPM VITE based Frontend Compilation
* Building Installers for Windows
* ZIP/UNZIP for Linux
* Docker Support
* Codesigning
* Signature Generation

## Usage
Called with
````
uv run -m rsjbuild  [globalOptions]... <verb> [options]... 
````

Global Options:
    --config Configuration File ( default: build.json) Can also be in environment as RSJBUILD_CONFIG
    --version Displays version
    --help Displays help

Verbs:
    init Creates build directory
    build Builds distribution
    keytool Creates Keytool
    version Displays version

## init
Options:
    --force Force recreation of build directory

## build

Options:
    --buildEmbed Creates embedded environment
    --withInstaller Creates Installer for Windows
    --sign Signs Windows Installer (Authenticode)
    --withZip Creates zip files for Linux
    --withUnzip Extracts zip files for Linux
    --publish Publishes files
    --upload Uploads files 
    --noConsole Do not show console in executables (on Windows)
    --force Force rebuild of all executables
    
## keytool
Create keyfile.

Options:
    --keyConfig Keytool Configuration File ( default: keytool.json) Can also be in environment as KEYTOOL_CONFIG
    --expiration Expiration time in days
    --expirationMinutes Expiration time in minutes
    --licensee Licensee
    --email Licensee Email
    --min Min Version
    --max Max Version
    --template Template File
    output File

## version
Show version


Note: [Cloud based Key Management is discussed](kms.md) 