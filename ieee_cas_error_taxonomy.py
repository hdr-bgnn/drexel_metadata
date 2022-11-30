#!/usr/bin/env python

import sqlite3
from typing import List, Union

DB = "./ieee-cas-label-checking-final.sqlite"

if __name__ == "__main__":
    con = sqlite3.connect(DB)
    cur = con.cursor()

    total = 0
        
    def show_taxon(name: str, err_types: Union[str, List[str]], *descr_kwds: str) -> None:
        if type(err_types) is str:
            err_types = [err_types]
        err_types_list = "(" + ",".join([f"'{err}'" for err in err_types]) + ")"
        query = f"select count(*) from results where err_type in {err_types_list}"
        if descr_kwds:
            query += " and (0"
            for kwd in descr_kwds:
                query += f" or lower(description) like '%{kwd}%'"
            query += ")"
        query += ";"
        res = cur.execute(query).fetchone()[0]
        global total
        total += res
        print("{: <32} {: >10}".format(name, res))

    show_taxon("OCR error", "ocr")
    show_taxon("> Underline", "ocr", "underline")
    show_taxon("> Poor contrast", "ocr", "contrast", "fade", "light")
    show_taxon("> Italic font", "ocr", "italic")
    show_taxon("> Handwritten or ruler noise", "ocr", "handwritten", "ruler")
    show_taxon("> Official name list discrepancy", "ocr", "canonical")
    show_taxon("> Text holes and smudging", "ocr", "damage", "smudge")
    show_taxon("Complex name format", "complex_name_format")
    show_taxon("Inadmissibility", "inadmissibility")
    show_taxon("Potential metadata error", "synonym")
    show_taxon("Confirmed metadata error", "true_error")
    show_taxon("Total", ["ocr", "complex_name_format", "inadmissibility", "synonym", "true_error"])

    con.close()
