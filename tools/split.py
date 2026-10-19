#!/usr/bin/env python3
"""Texto por capítulos de The Come Up: An Oral History of the Rise of Hip-Hop (Jonathan Abrams, Crown, 2022).

Uso: python3 -I tools/split.py <dir_xhtml> <dir_salida>

Lee directamente los XHTML del ePub, que traen la paginación impresa (marcas epub:type="pagebreak").
Capítulo 1: la nota del autor; 2-24: los capítulos 01-23 del libro. Las cabeceras (número, título,
lugar y años) salen como «## …»; las notas al pie se descartan. Escribe <dir>/NN.txt (un párrafo por
línea, «[pág. N]» con la página impresa en que empieza) y <dir>/book.json (párrafos {ch, sec, segs:
[[pág, texto]]}, el formato de tools/refs.py y de pdfpages.py --impresas; sec es la cabecera de lugar).
"""
import html
import json
import re
import sys
from pathlib import Path

FILES = {1: 'ant'} | {n + 1: f'c{n:03d}' for n in range(1, 24)}
BREAK = re.compile(r'<span[^>]*epub:type="pagebreak"[^>]*title="([^"]+)"[^>]*/>')
PARA = re.compile(r'<(p|h[1-6])\b([^>]*)>(.*?)</\1>', re.S)


def clean(s):
    s = re.sub(r'<a[^>]*footnote_ref[^>]*>.*?</a>', '', s, flags=re.S)
    s = re.sub(r'<sup[^>]*>.*?</sup>', '', s, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def page_of(t):
    return int(t) if t.isdigit() else t


def main(src, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paras = []
    for ch, name in FILES.items():
        doc = next(Path(src).glob(f'*_{name}_r1.xhtml')).read_text()
        body = doc[doc.index('<body'):]
        page, sec, text, heads = None, None, [], []
        pos = 0
        for m in PARA.finditer(body):
            for b in BREAK.findall(body[pos:m.start()]):
                page = page_of(b)
            pos = m.end()
            tag, attrs, inner = m.groups()
            if 'footnote' in attrs:
                continue
            parts = BREAK.split(inner)          # [texto, pág, texto, pág, …]
            segs, cur = [], page
            for i, part in enumerate(parts):
                if i % 2:
                    cur = page_of(part)
                    continue
                t = clean(part)
                if t:
                    segs.append([cur, t])
            page = cur
            if not segs:
                continue
            line = ' '.join(t for _, t in segs)
            if tag != 'p':
                heads.append(line)
                text.append(f'## {line}')
                continue
            if len(heads) >= 3 and sec is None:
                sec = heads[2]                  # el lugar («Bronx, New York»)
            paras.append({'ch': ch, 'sec': sec, 'segs': segs})
            text.append(f'[pág. {segs[0][0]}] {line}')
        (out / f'{ch:02d}.txt').write_text('\n\n'.join(text) + '\n')
        n = sum(len(t.split()) for p in paras if p['ch'] == ch for _, t in p['segs'])
        print(f'cap. {ch}: {n} palabras, págs. {next((p["segs"][0][0] for p in paras if p["ch"] == ch), "?")}–{page}')
    (out / 'book.json').write_text(json.dumps(paras, ensure_ascii=False))


if __name__ == '__main__':
    main(*sys.argv[1:])
