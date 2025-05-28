import argparse
import pathlib
import json
import glob
import logging
import datetime

logger = logging.getLogger(__name__)

import polib
import six
import jinja2

class LanguageFile(polib.POFile):
    def __init__(self, encoding="utf-8-sig", **kwargs):
        super().__init__(encoding=encoding, **kwargs)
        now=datetime.datetime.now(datetime.UTC)
        nowString=now.isoformat(" ")[:16]+"+0000"
        self.metadata= {
                        "Project-Id-Version": "1.0",
                        "Report-Msgid-Bugs-To": "info@rsj.de",
                        "POT-Creation-Date": nowString,
                        "PO-Revision-Date": nowString,
                        "Last-Translator": "Ruediger Jungbeck <ruediger.jungbeck@rsj.de>",
                        "Language-Team": "English <info@rsj.de>",
                        "MIME-Version": "1.0",
                        "Content-Type": "text/plain; charset=utf-8",
                        "Content-Transfer-Encoding": "8bit"
                        }

    def __iadd__(self, other):

        for otherEntry in other:
            selfEntry=self.find(otherEntry.msgid, include_obsolete_entries=True)
            if selfEntry is None:
                self.append(otherEntry)
            else:
                selfEntry.occurrences+=otherEntry.occurrences
                selfEntry.obsolete = False
                if otherEntry.msgctxt:
                    selfEntry.msgctxt=otherEntry.msgctxt
        return self

    def __add__(self, other):
        ret=LanguageFile(encoding="utf-8")
        ret+=self
        ret+=other
        return ret

    def __radd__(self, other):
        if not other:
            return self
        return other+self

    def translated(self, include_obsolete_entries=True):
        ret=LanguageFile()
        for entry in self.translated_entries():
            if include_obsolete_entries or not entry.obsolete:
                ret.append(entry)
        return ret

    def untranslated(self, include_obsolete_entries=False):
        ret=LanguageFile()
        for entry in self.untranslated_entries():
            if include_obsolete_entries or not entry.obsolete:
                ret.append(entry)
        return ret

    def reset(self):
        for entry in self:
            entry.obsolete=True
            entry.occurrences=[]

def add(target, source):
    for ent in source:
        poe=target.find(ent.msgid)
        if not poe:
            target.append(ent)
        else:
            poe.occurences+=ent.occurrences
            poe.obsolete&=ent.obsolete

def load(inFile):
    inPath=pathlib.Path(inFile)

    if inPath.suffix in [".po", ".pot"]:
        po=polib.pofile(inFile, encoding="utf-8-sig")
        po.save_as_pofile=po.save

    elif inPath.suffix==".mo":
        po = polib.mofile(inFile, encoding="utf-8")
        po.save_as_mofile=po.save

    elif inPath.suffix==".json":

        po=polib.POFile(encoding="utf-8")
        po.save_as_pofile=po.save

        with inPath.open("r", encoding="utf-8") as inputFile:
            contents=json.load(inputFile)

            for k, v in six.iteritems(contents):
                poe=po.find(k)
                if not poe:
                    poe = polib.POEntry(msgid=k, obsolete=False)
                    po.append(poe)
                for v1 in v:
                    vn, vl = v1.split(": ")
                    print(vn, int(vl))
                    poe.occurrences += [(vn, vl)]

    else:
        po = polib.POFile(encoding="utf-8")
        po.save_as_pofile = po.save

        with inPath.open("r", encoding="utf-8-sig") as inputFile:
            template=inputFile.read()
            env=jinja2.Environment(loader=jinja2.FileSystemLoader,
                                    extensions=["jinja2.ext.i18n"])
            env.parse(template)
            for t in env.extract_translations(template):
                poe=po.find(t[2])
                if not poe:
                    poe=polib.POEntry(msgid=t[2], obsolete=False)
                    po.append(poe)
                poe.occurrences+=[(inPath, t[0])]


    return po


def parseJINJA2(fileName):
    inPath=pathlib.Path(fileName)
    po = LanguageFile(encoding="utf-8")
    po.save_as_pofile = po.save

    with open(fileName, "r", encoding="utf-8-sig") as inputFile:
        template = inputFile.read()
        env = jinja2.Environment(loader=jinja2.FileSystemLoader,
                                 extensions=["jinja2.ext.i18n"])
        env.parse(template)
        for t in env.extract_translations(template):
            poe = po.find(t[2])
            if not poe:
                poe = polib.POEntry(msgid=t[2], obsolete=False)
                po.append(poe)

            poe.occurrences += [(inPath, t[0])]
    return po

def save(po, outFile):
    outPath = pathlib.PurePath(outFile)

    if outPath.suffix in [".po", ".pot"]:
        po.save_as_pofile(outFile)

    elif outPath.suffix == ".mo":
        po.save_as_mofile(outFile)

def main():
    parser = argparse.ArgumentParser(description="PO Tool",
                                   epilog="(C) Copyright 2018-2019 by RSJ Software GmbH Stockdorf. All rights reserved.",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--remove", action="store_true", help="Remove obsolete translations")
    parser.add_argument("--poFile", type=str, help="Output file (.po)")
    parser.add_argument("--moFile", type=str, help="Output file (.mo)")
    parser.add_argument("--translate", type=str,  help="Translationion language for missing strings via Google Translate")
    parser.add_argument("--translatePo", type=str, help="PO file from translation")
    parser.add_argument("inFile", type=str, nargs="+", help="Input file")
    parms = parser.parse_args()

    doMain(parms)

def doMain(parms):
    combined=LanguageFile(encoding="utf-8")

    if parms.poFile:
        try:
            po=polib.pofile(parms.poFile, encoding="utf-8-sig", klass=LanguageFile)
            po.reset()
            combined+=po
        except Exception:
            pass

    for inFileMask in parms.inFile:
        for inFileName in glob.glob(inFileMask):

            try:
                inPath=pathlib.Path(inFileName)

                if inPath.suffix in [".po", ".pot"]:
                    thisFile=polib.pofile(inFileName, encoding="utf-8-sig", klass=LanguageFile)
                else:
                    thisFile=parseJINJA2(inFileName)

                combined+=thisFile
            except (IsADirectoryError, PermissionError):
                pass
            except Exception:
                logging.exception(inFileName)


    if parms.translate:
        from google.cloud import translate_v3beta1 as translate
        client = translate.TranslationServiceClient()

        project_id = "translate-171419"
        # text = 'Text you wish to translate'
        location = 'global'

        parent = client.location_path(project_id, location)

        po = polib.POFile(encoding="utf-8", klass=LanguageFile)
        po.save_as_pofile = po.save

        for poe in combined.translated():
            po.append(poe)

        for poe in combined.untranslated():
            #print(poe.msgid)

            response = client.translate_text(
                parent=parent,
                contents=[poe.msgid],
                mime_type='text/plain',  # mime types: text/plain, text/html
                source_language_code='en-US',
                target_language_code=parms.translate)

            if len(response.translations):
                targetText=response.translations[0].translated_text

                print(targetText)

                if targetText:
                    poeOut = polib.POEntry(msgid=poe.msgid, msgstr=targetText, occurrences=poe.occurrences, obsolete=False)
                    po.append(poeOut)

        if parms.translatePo:
            po.save(parms.translatePo)

        combined+=po


    result=combined.translated(include_obsolete_entries=not parms.remove)+combined.untranslated()

    if parms.poFile:
        result.save(parms.poFile)

    if parms.moFile:
        mo=LanguageFile(encoding="utf-8")
        mo+=result
        mo.save_as_mofile(parms.moFile)

if __name__=="__main__":
    main()
