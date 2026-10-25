#!/usr/bin/env python3
"""Playwright layout checks for home interlinking (spec §5 AC10 as it applies to / /ru/ /zh/).

No screenshots (PNG reads crash this agent). Measures:
  documentElement.scrollWidth <= documentElement.clientWidth
  Popular + footer + new interactive targets >= 44px
  brand stays on one line

Usage: python3 tools/test_layout.py
Needs: pip install playwright; playwright browsers (channel=chrome if present).
Serves the repo root on 127.0.0.1:$E2E_PORT (default 8765)."""
from __future__ import annotations

import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PORT = int(os.environ.get('E2E_PORT', '8765'))
PAGES = ['/', '/ru/', '/zh/']
WIDTHS = [280, 320, 375, 768, 1280]
THEMES = [
    ('light', {'color_scheme': 'light'}, None),
    ('dark', {'color_scheme': 'dark'}, 'lagoon-dark'),
]
RES = []


def ok(name, cond, info=''):
    RES.append((name, bool(cond), info))
    print(('PASS ' if cond else 'FAIL ') + name + (('  ' + str(info)) if info and not cond else ''))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def serve():
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer(('127.0.0.1', PORT), partial(QuietHandler, directory=ROOT))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


MEASURE = """() => {
  const de = document.documentElement;
  const brand = document.querySelector('.brand');
  const br = brand.getBoundingClientRect();
  const targets = [...document.querySelectorAll('.pop a, .ft a, .btn, .langs a, .skip, .mt a')].map(el => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      tag: (el.className || el.tagName) + ':' + (el.textContent || '').trim().slice(0, 40),
      w: Math.round(r.width), h: Math.round(r.height),
      vis: r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'
    };
  }).filter(t => t.vis);
  const small = targets.filter(t => t.h < 44);
  const ft = document.querySelector('nav.ft');
  const pops = document.querySelectorAll('ul.pop');
  return {
    scroll: de.scrollWidth,
    client: de.clientWidth,
    overflow: de.scrollWidth - de.clientWidth,
    brandH: Math.round(br.height),
    brandWrap: getComputedStyle(brand).whiteSpace === 'nowrap' || Math.round(br.height) <= 44,
    small,
    ft: !!ft,
    popCount: pops.length,
    targetCount: targets.length
  };
}"""


def launch(p):
    chromium = p.chromium
    last = None
    for kwargs in (
        {'channel': 'chrome'},
        {'channel': 'chromium'},
        {},
    ):
        try:
            return chromium.launch(**kwargs)
        except Exception as e:
            last = e
    raise RuntimeError(f'could not launch chromium: {last}')


def main():
    httpd = serve()
    base = f'http://127.0.0.1:{PORT}'
    with sync_playwright() as p:
        browser = launch(p)
        try:
            for theme, ctx_kw, data_theme in THEMES:
                ctx = browser.new_context(**ctx_kw)
                page = ctx.new_page()
                for path in PAGES:
                    for wd in WIDTHS:
                        page.set_viewport_size({'width': wd, 'height': 900})
                        page.goto(base + path, wait_until='load')
                        if data_theme:
                            page.evaluate(
                                "(t) => document.documentElement.setAttribute('data-theme', t)",
                                data_theme,
                            )
                        page.wait_for_timeout(50)
                        m = page.evaluate(MEASURE)
                        label = f'{theme} {wd} {path}'
                        ok(f'{label}: scrollWidth<=clientWidth',
                           m['overflow'] <= 0,
                           f"{m['scroll']}>{m['client']}")
                        ok(f'{label}: Popular+footer present',
                           m['ft'] and m['popCount'] == 2, m)
                        ok(f'{label}: new targets >=44px',
                           not m['small'], m['small'][:6])
                        ok(f'{label}: brand one line',
                           m['brandWrap'] and m['brandH'] <= 44, m['brandH'])
                ctx.close()
        finally:
            browser.close()
    httpd.shutdown()
    failed = [r for r in RES if not r[1]]
    print(f'\n{len(RES) - len(failed)}/{len(RES)} passed')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
