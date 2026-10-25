#!/usr/bin/env python3
"""Checker for interlinking spec 2026-10 §5 AC1–AC9 as they apply to the home repo.

Home scope: / /ru/ /zh/ via tools/genhome.py — §3.1 Popular links + §3.4 footer.
AC3 (converter/pdf contextual) and AC6 (breadcrumbs/JSON-LD) are out of scope.
Run: python3 tools/test_interlinking.py
Exit 0 only if every applicable check passes. Re-running genhome.py must leave HTML unchanged."""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import subprocess
import sys
from collections import Counter
from urllib.parse import urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(ROOT)
LANGS = ['en', 'ru', 'zh']
PAGES = {
    'en': 'index.html',
    'ru': 'ru/index.html',
    'zh': 'zh/index.html',
}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
       "base-uri 'none'; form-action 'none'; object-src 'none'")
ALLOWED_HOSTS = {'', 'noclaudkit.com'}
FT_HREFS = {
    'en': ['/', '/image-converter/', '/pdf/', '/image-converter/heic-to-jpg.html',
           '/pdf/merge-pdf.html', '/pdf/split-pdf.html', '/pdf/jpg-to-pdf.html'],
    'ru': ['/ru/', '/image-converter/ru/', '/pdf/ru/', '/image-converter/ru/heic-to-jpg.html',
           '/pdf/ru/merge-pdf.html', '/pdf/ru/split-pdf.html', '/pdf/ru/jpg-to-pdf.html'],
    'zh': ['/zh/', '/image-converter/zh/', '/pdf/zh/', '/image-converter/zh/heic-to-jpg.html',
           '/pdf/zh/merge-pdf.html', '/pdf/zh/split-pdf.html', '/pdf/zh/jpg-to-pdf.html'],
}
FT_LABELS = {
    'en': ['NoClaudKit', 'Image converter', 'PDF tools', 'HEIC to JPG', 'Merge PDF', 'Split PDF', 'JPG to PDF'],
    'ru': ['NoClaudKit', 'Конвертер изображений', 'Инструменты для PDF', 'HEIC в JPG', 'Объединить PDF', 'Разделить PDF', 'JPG в PDF'],
    'zh': ['NoClaudKit', '图片转换器', 'PDF 工具', 'HEIC 转 JPG', '合并 PDF', '拆分 PDF', '图片转 PDF'],
}
POP = {
    'en': [('/image-converter/heic-to-jpg.html', 'HEIC to JPG'),
           ('/pdf/merge-pdf.html', 'Merge PDF'),
           ('/pdf/split-pdf.html', 'Split PDF'),
           ('/pdf/jpg-to-pdf.html', 'JPG to PDF')],
    'ru': [('/image-converter/ru/heic-to-jpg.html', 'HEIC в JPG'),
           ('/pdf/ru/merge-pdf.html', 'Объединить PDF'),
           ('/pdf/ru/split-pdf.html', 'Разделить PDF'),
           ('/pdf/ru/jpg-to-pdf.html', 'JPG в PDF')],
    'zh': [('/image-converter/zh/heic-to-jpg.html', 'HEIC 转 JPG'),
           ('/pdf/zh/merge-pdf.html', '合并 PDF'),
           ('/pdf/zh/split-pdf.html', '拆分 PDF'),
           ('/pdf/zh/jpg-to-pdf.html', '图片转 PDF')],
}
CANON = {
    'en': 'https://noclaudkit.com/',
    'ru': 'https://noclaudkit.com/ru/',
    'zh': 'https://noclaudkit.com/zh/',
}
HREFLANG = {'en': 'en', 'ru': 'ru', 'zh': 'zh-Hans'}
HEAD_ALTS = (
    '<link rel="canonical" href="{canon}">'
    '<link rel="alternate" hreflang="en" href="https://noclaudkit.com/">'
    '<link rel="alternate" hreflang="ru" href="https://noclaudkit.com/ru/">'
    '<link rel="alternate" hreflang="zh-Hans" href="https://noclaudkit.com/zh/">'
    '<link rel="alternate" hreflang="x-default" href="https://noclaudkit.com/">'
)
NB = '\u00a0'
FAILS = []
GEN_TRACKED = [
    'index.html', 'ru/index.html', 'zh/index.html', '404.html',
    'CNAME', 'robots.txt', 'sitemap.xml', 'sitemap-home.xml',
]


def load(lang):
    return open(PAGES[lang], encoding='utf-8').read()


def fail(ac, msg):
    FAILS.append(f'AC{ac}: {msg}')
    print('FAIL', f'AC{ac}: {msg}')


def ok(ac, msg):
    print('PASS', f'AC{ac}: {msg}')


def norm(s):
    return re.sub(r'\s+', ' ', html.unescape(s).replace(NB, ' ')).strip()


def site_lang(path):
    parts = [p for p in path.split('/') if p]
    if not parts:
        return 'en'
    if parts[0] in ('ru', 'zh'):
        return parts[0]
    if parts[0] in ('image-converter', 'pdf'):
        if len(parts) > 1 and parts[1] in ('ru', 'zh'):
            return parts[1]
        return 'en'
    return None


def href_path(href):
    if href.startswith('https://noclaudkit.com'):
        return urlparse(href).path or '/'
    if href.startswith('/'):
        return href.split('?', 1)[0]
    return None


def is_switcher(tag):
    return 'hreflang=' in tag or 'Read in English' in tag


def each_anchor(s):
    for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', s, re.S):
        yield m.group(1), m.group(2)


def ac1():
    bad = []
    for lang in LANGS:
        s = load(lang)
        ft = re.search(r'<nav class="ft"[^>]*>(.*?)</nav>', s, re.S)
        if not ft:
            bad.append(f'{lang}: no .ft nav')
            continue
        hrefs = re.findall(r'<a href="([^"]*)"', ft.group(1))
        texts = [norm(re.sub(r'<[^>]+>', '', x)) for x in re.findall(r'<a\b[^>]*>(.*?)</a>', ft.group(1), re.S)]
        if hrefs != FT_HREFS[lang]:
            bad.append(f'{lang}: footer hrefs {hrefs}')
        if texts != FT_LABELS[lang]:
            bad.append(f'{lang}: footer labels {texts}')
        home = re.search(r'<nav class="ft"[^>]*>.*?<a href="([^"]*)"[^>]*>NoClaudKit</a>', s, re.S)
        if not home or home.group(1) != FT_HREFS[lang][0]:
            bad.append(f'{lang}: missing same-language home link')
        if 'aria-current="page"' not in ft.group(0):
            bad.append(f'{lang}: home footer link missing aria-current')
        for tag, _inner in each_anchor(s):
            hm = re.search(r'href="([^"]*)"', tag)
            if not hm or is_switcher(tag):
                continue
            href = hm.group(1)
            path = href_path(href)
            if path is None:
                continue
            hl = site_lang(path)
            if hl and hl != lang:
                bad.append(f'{lang}: cross-language href {href}')
    if bad:
        for b in bad:
            fail(1, b)
    else:
        ok(1, '3 home pages have the 7-link same-language footer and no cross-language hrefs outside the switcher')


def ac2():
    bad = []
    for lang in LANGS:
        s = load(lang)
        pops = re.findall(r'<ul class="pop">(.*?)</ul>', s, re.S)
        if len(pops) != 2:
            bad.append(f'{lang}: expected 2 Popular lists, got {len(pops)}')
            continue
        pairs = []
        for block in pops:
            for m in re.finditer(r'<a href="([^"]*)">(.*?)</a>', block, re.S):
                pairs.append((m.group(1), norm(m.group(2))))
        if pairs != POP[lang]:
            bad.append(f'{lang}: Popular links {pairs}')
        if 'webp-to-png' in s:
            bad.append(f'{lang}: webp-to-png must not appear')
        soon = re.findall(r'<div class="card soon">(.*?)</div></li>', s, re.S)
        if len(soon) != 2:
            bad.append(f'{lang}: expected 2 coming-soon cards, got {len(soon)}')
        for block in soon:
            if '<a ' in block or 'href=' in block:
                bad.append(f'{lang}: coming-soon card has a link')
    if bad:
        for b in bad:
            fail(2, b)
    else:
        ok(2, 'home en/ru/zh Popular links to same-language heic/merge/split/jpg-to-pdf; no webp-to-png')


def ac4():
    bad = []
    skip_hash = {'#', '#main', '#dl'}
    for lang in LANGS:
        s = load(lang)
        for tag, _inner in each_anchor(s):
            hm = re.search(r'href="([^"]*)"', tag)
            if not hm:
                continue
            href = hm.group(1)
            if 'rel="nofollow"' in tag or 'onclick=' in tag:
                bad.append(f'{lang}: nofollow/onclick on {href}')
            if re.search(r'[?&]utm_|[?&]ref=', href, re.I):
                bad.append(f'{lang}: utm/ref on {href}')
            if '#' in href:
                frag = '#' + href.split('#', 1)[1]
                if frag not in skip_hash:
                    bad.append(f'{lang}: hash href {href}')
            path = href_path(href)
            if path and not path.endswith('/') and not path.endswith('.html') and site_lang(path) is not None:
                bad.append(f'{lang}: hub href missing trailing slash: {href}')
    if bad:
        for b in bad:
            fail(4, b)
    else:
        ok(4, 'no utm/ref/# (except #main), no nofollow/onclick; hub hrefs use trailing slash')


def ac5():
    bad = []
    banned = re.compile(r'\b(free|online|without upload|онлайн)\b', re.I)
    for lang in LANGS:
        s = load(lang)
        body = re.sub(r'<script[^>]*>.*?</script>', '', s, flags=re.S)
        texts = []
        for tag, inner in each_anchor(body):
            t = norm(re.sub(r'<[^>]+>', '', inner))
            if not t:
                continue
            if banned.search(t):
                bad.append(f'{lang}: banned word in anchor {t!r}')
            if is_switcher(tag):
                continue
            texts.append(t)
        for t, n in Counter(texts).items():
            if n > 2:
                bad.append(f'{lang}: anchor {t!r} appears {n}×')
    if bad:
        for b in bad:
            fail(5, b)
    else:
        ok(5, 'no exact interlink anchor > 2×; no free/online in anchors')


def ac7():
    bad = []
    hosts = set()
    for lang in LANGS:
        s = load(lang)
        m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">', s)
        if not m or m.group(1) != CSP:
            bad.append(f'{lang}: CSP changed')
        for val in re.findall(r'''\b(?:href|src|srcset)=["']([^"']+)["']''', s):
            u = urlparse(val)
            if u.scheme in ('http', 'https') and u.hostname:
                hosts.add(u.hostname)
        for j in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            for u in re.findall(r'https://([^/"\']+)', j):
                hosts.add(u)
    extra = hosts - ALLOWED_HOSTS
    if extra:
        bad.append(f'new external hosts: {sorted(extra)}')
    if bad:
        for b in bad:
            fail(7, b)
    else:
        ok(7, f'CSP meta byte-identical; hosts={sorted(hosts)}')


def ac8():
    before = {p: hashlib.sha256(open(p, 'rb').read()).hexdigest() for p in GEN_TRACKED}
    r = subprocess.run([sys.executable, 'tools/genhome.py'], capture_output=True, text=True)
    if r.returncode != 0:
        fail(8, 'genhome.py failed:\n' + (r.stderr or r.stdout)[-2000:])
        return
    changed = [p for p, h in before.items() if hashlib.sha256(open(p, 'rb').read()).hexdigest() != h]
    if changed:
        fail(8, 'generator rerun rewrote: ' + ', '.join(changed))
    else:
        ok(8, 'generator rerun = zero diff')


def ac9():
    bad = []
    for lang in LANGS:
        s = load(lang)
        want = HEAD_ALTS.format(canon=CANON[lang])
        if want not in s:
            bad.append(f'{lang}: canonical/hreflang block not byte-identical')
        if s.count('<link rel="canonical"') != 1:
            bad.append(f'{lang}: expected exactly one canonical')
        alts = re.findall(r'<link rel="alternate" hreflang="([^"]*)" href="([^"]*)">', s)
        expect = [(HREFLANG[l], CANON[l]) for l in LANGS] + [('x-default', CANON['en'])]
        if alts != expect:
            bad.append(f'{lang}: hreflang {alts} != {expect}')
    if bad:
        for b in bad:
            fail(9, b)
    else:
        ok(9, 'canonical + hreflang byte-identical to the pre-interlinking scheme')


def extras():
    bad = []
    il = json.load(open('tools/i18n/interlink.json', encoding='utf-8'))
    for lang in LANGS:
        s = load(lang)
        if 'PDF-инструменты' in s.replace('\u2011', '-'):
            bad.append(f'{lang}: PDF-инструменты still present')
        if re.search(r'\sstyle=', s):
            bad.append(f'{lang}: inline style=')
        scripts = re.findall(r'<script\b([^>]*)>', s)
        for attrs in scripts:
            if 'src=' not in attrs:
                bad.append(f'{lang}: unexpected inline script {attrs}')
        if '<nav class="crumbs"' in s or 'application/ld+json' in s:
            bad.append(f'{lang}: breadcrumbs/JSON-LD must not appear on home')
        for a in re.findall(r'aria-label="([^"]*)"', s):
            if NB in html.unescape(a):
                bad.append(f'{lang}: NBSP in aria-label')
        if lang == 'ru':
            ft = re.search(r'<nav class="ft"[^>]*>(.*?)</nav>', s, re.S).group(1)
            if 'HEIC в JPG' in ft or 'JPG в PDF' in ft:
                bad.append('ru: visible footer missing NBSP after в')
            if 'HEIC в\u00a0JPG' not in ft or 'JPG в\u00a0PDF' not in ft:
                bad.append('ru: expected NBSP after в in footer anchors')
        got = [il[lang][k] for k in ('ft_home', 'f_conv', 'f_pdf', 'ft_heic', 'ft_merge', 'ft_split', 'ft_jpg')]
        if [norm(x) for x in got] != FT_LABELS[lang]:
            bad.append(f'{lang}: interlink.json labels {got}')
    src = open('tools/genhome.py', encoding='utf-8').read() + open('tools/i18n/interlink.json', encoding='utf-8').read()
    if 'PDF-инструменты' in src:
        bad.append('source still contains PDF-инструменты')
    if bad:
        for b in bad:
            fail('x', b)
    else:
        ok('x', 'no PDF-инструменты; no inline style/script; no crumbs/JSON-LD; ru NBSP in visible text only')


def main():
    ac1()
    ac2()
    print('SKIP AC3: converter/pdf contextual links are out of scope for the home repo')
    ac4()
    ac5()
    print('SKIP AC6: breadcrumbs + JSON-LD are not on home pages (spec §3.1)')
    ac7()
    ac8()
    ac9()
    extras()
    print(f'\n{len(FAILS)} failed')
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
