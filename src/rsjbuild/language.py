import pathlib
import sys
import logging

logger = logging.getLogger(__name__)

import addict

from .utils import system
from .potool import doMain

def procMessages(sourcePath, mainModule):
    pythonPath = pathlib.Path(sys.executable).parent

    pyBabel = str(pythonPath / "pybabel")

    system(f"{pyBabel} extract -o build/messages.pot --input-dirs={str(sourcePath)} --ignore-dirs=*")

    for poPath in pathlib.Path("locale").rglob(f"LC_MESSAGES/{mainModule}.po"):
        moPath = poPath.with_suffix(".mo")

        poControl = {
            "remove": False,
            "poFile": str(poPath),
            "moFile": str(moPath),
            "translate": None,
            "translatePo": None,
            "inFile": ["build/messages.pot"]
            }

        poControl = addict.Dict(poControl)

        doMain(poControl)
        #pythonCall(f"tool/potool.py --poFile {str(poPath)} --moFile {str(moPath)} build/messages.pot")