#!/usr/bin/env python3
"""Unit tests for home SEO validation and escaping in tools/genhome.py."""
from __future__ import annotations

import importlib.util
import json
import os
import random
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SEO_PATH = os.path.join(ROOT, 'tools', 'i18n', 'home-seo.json')


def _load_genhome():
    path = os.path.join(ROOT, 'tools', 'genhome.py')
    spec = importlib.util.spec_from_file_location('genhome', path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


gh = _load_genhome()


class EditorialGuardTests(unittest.TestCase):
  def assert_rejects(self, html):
    err = gh.validate_editorial_html(html)
    self.assertTrue(err, f'expected rejection for {html!r}')

  def test_real_home_seo_passes(self):
    with open(SEO_PATH, encoding='utf-8') as f:
      seo = json.load(f)
    for lang in ('en', 'ru', 'zh'):
      with self.subTest(lang=lang):
        err = gh.validate_editorial_html(seo[lang]['home']['editorial_html'])
        self.assertEqual(err, [], err)

  def test_p_hidden_rejected(self):
    self.assert_rejects('<p hidden>x</p>')

  def test_p_style_rejected(self):
    self.assert_rejects('<p style="color:red">x</p>')

  def test_p_class_rejected(self):
    self.assert_rejects('<p class="x">x</p>')

  def test_a_onclick_rejected(self):
    self.assert_rejects('<p><a href="/pdf/" onclick="alert(1)">x</a></p>')

  def test_href_backslash_evil(self):
    self.assert_rejects('<p><a href="/\\evil.com">x</a></p>')

  def test_href_entity_tab_bypass(self):
    self.assert_rejects('<p><a href="/&#9;/evil.com">x</a></p>')

  def test_href_protocol_relative(self):
    self.assert_rejects('<p><a href="//evil.com">x</a></p>')

  def test_href_javascript_scheme(self):
    self.assert_rejects('<p><a href="javascript:alert(1)">x</a></p>')
    self.assert_rejects('<p><a href="/javascript:alert(1)">x</a></p>')

  def test_unclosed_tag(self):
    self.assert_rejects('<p>one<p>two</p>')

  def test_misnesting_ul_in_p(self):
    self.assert_rejects('<p><ul><li>x</li></ul></p>')

  def test_unallowed_tag(self):
    self.assert_rejects('<p><img src="/x"></p>')

  def test_cdata_bypass_rejected(self):
    self.assert_rejects(
      '<![CDATA[ x > <a href="//evil.com">x</a> <p hidden>y]]>',
    )

  def test_comment_bypass_ending_rejected(self):
    self.assert_rejects('<!-- x --!> <a href="//evil.com">')

  def test_processing_instruction_rejected(self):
    self.assert_rejects('<?pi?><p>x</p>')

  def test_doctype_rejected(self):
    self.assert_rejects('<!DOCTYPE html><p>x</p>')

  def test_trailing_unclosed_anchor_rejected(self):
    self.assert_rejects('<p>safe<a href="//evil.example/x"')

  def test_partial_open_and_close_rejected(self):
    self.assert_rejects('<p>x<a href="//e"')
    self.assert_rejects('<p')
    self.assert_rejects('x</p')
    self.assert_rejects('before<after')
    self.assert_rejects('x>y')

  def test_whitespace_and_quote_variants_rejected(self):
    self.assert_rejects('<p >x</p>')
    self.assert_rejects('<a  href="/x">t</a>')
    self.assert_rejects("<a href='/x'>t</a>")

  def test_fuzz_insertions_reject_or_unchanged(self):
    with open(SEO_PATH, encoding='utf-8') as f:
      base = json.load(f)['en']['home']['editorial_html']
    frags = ('<', '>', '</', '<p', '</p', '<a', '<a href="//e"', '<a href="', '">', '</a>', '<x>')
    rng = random.Random(0)
    for _ in range(600):
      s = base
      for _ in range(rng.randint(1, 4)):
        pos = rng.randint(0, len(s))
        s = s[:pos] + rng.choice(frags) + s[pos:]
      err = gh.validate_editorial_html(s)
      if not err:
        self.assertEqual(s, base, 'only unmodified copy may pass fuzz')


class EscapeTests(unittest.TestCase):
  def test_h1_escapes_lt_and_amp(self):
    self.assertEqual(
      gh.hero_h1('Tools & tricks <test>'),
      '<h1>Tools &amp; tricks &lt;test&gt;</h1>',
    )

  def test_valid_rel_href_ok(self):
    self.assertTrue(gh.valid_rel_href('/image-converter/heic-to-jpg.html'))
    self.assertTrue(gh.valid_rel_href('/pdf/ru/merge-pdf.html'))

  def test_valid_rel_href_bad(self):
    self.assertFalse(gh.valid_rel_href('//evil.com'))
    self.assertFalse(gh.valid_rel_href('/\\evil.com'))
    self.assertFalse(gh.valid_rel_href('/&#9;/x'))


if __name__ == '__main__':
  unittest.main()
