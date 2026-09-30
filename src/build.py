#!/usr/bin/env python3
"""
Solvata static site builder.

  index.tpl.html       + index.i18n.json       -> index.html            (DE)   en/index.html      (EN)
  leistungen.tpl.html  + leistungen.i18n.json  -> leistungen.html      (DE)   en/treatments.html (EN)

Edit texts in the *.i18n.json files, structure/CSS in the *.tpl.html files,
then run:   python3 build.py
Output is written to the parent directory of this folder.

Requires: pip install beautifulsoup4
"""
import json, os, re
from bs4 import BeautifulSoup, Tag, Comment

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

# TODO: replace with the real domain (used in canonical / hreflang / sitemap / JSON-LD)
BASE = 'https://YOUR-DOMAIN.de'
# TODO: replace with a real 1200x630 share image once it exists
OG_IMAGE = 'https://ik.imagekit.io/erewhile/Solvata/logo%20and%20og/180%20x%20180.png'

PAGES = {
    'index': {
        'path': {'de': 'index.html', 'en': 'en/index.html'},
        'meta': {
            'de': ('Solvata Beauty Club Berlin — Premium Kosmetik & Nägel',
                   'Solvata Beauty Club Berlin. Apparative Kosmetik, Gesichtspflege, Körperformung & Nageldesign. Berliner Straße 54, 10713 Berlin.'),
            'en': ('Solvata Beauty Club Berlin — Premium Cosmetics & Nails',
                   'Solvata Beauty Club Berlin. Advanced facial treatments, body contouring, laser hair removal and nail design. Berliner Straße 54, 10713 Berlin.'),
        },
    },
    'leistungen': {
        'path': {'de': 'leistungen.html', 'en': 'en/treatments.html'},
        'meta': {
            'de': ('Alle Behandlungen — Solvata Beauty Club Berlin',
                   'Vollständige Übersicht aller Gesichts- und Körperbehandlungen bei Solvata Beauty Club Berlin: BABOR Anti-Age, Dermapen, Endosphères, Laser und mehr.'),
            'en': ('All Treatments — Solvata Beauty Club Berlin',
                   'Complete overview of all facial and body treatments at Solvata Beauty Club Berlin: BABOR anti-aging, Dermapen, Endosphères, laser and more.'),
        },
    },
}

LINK_MAP = {  # DE file name -> EN file name (EN pages live in /en/)
    'leistungen.html': 'treatments.html',
    'index.html': 'index.html',
    'privacy-policy.html': '../privacy-policy.html',   # TODO: EN privacy page
}

def rel(from_lang, page, to_lang):
    """relative URL from a page in from_lang to the same page in to_lang"""
    to = PAGES[page]['path'][to_lang]
    if from_lang == 'en':
        return to[3:] if to.startswith('en/') else '../' + to
    return to

def meta(soup, attr, name, content):
    for m in soup.select(f'meta[{attr}="{name}"]'): m.decompose()
    t = soup.new_tag('meta'); t[attr] = name; t['content'] = content
    soup.head.append(t)

def build(page, lang):
    tpl = open(f'{HERE}/{page}.tpl.html', encoding='utf-8').read()
    T = json.load(open(f'{HERE}/{page}.i18n.json', encoding='utf-8'))[lang]
    tpl = tpl.replace('__LANG__', lang).replace('__PRIV__', '../privacy-policy.html' if lang == 'en' else 'privacy-policy.html')
    soup = BeautifulSoup(tpl, 'html.parser')
    soup.html['lang'] = lang

    # elements marked hidden in the template are left out of the published page
    for el in soup.select('[hidden]'): el.decompose()
    for c in soup.find_all(string=lambda x: isinstance(x, Comment)): c.extract()

    # text
    for el in soup.select('[data-i18n]'):
        k = el['data-i18n']
        if k in T:
            el.clear(); el.append(BeautifulSoup(T[k], 'html.parser'))
        del el['data-i18n']          # not needed in the static output

    # head
    title, desc = PAGES[page]['meta'][lang]
    soup.title.string = title
    meta(soup, 'name', 'description', desc)
    meta(soup, 'property', 'og:title', title)
    meta(soup, 'property', 'og:description', desc)
    meta(soup, 'property', 'og:type', 'website')
    meta(soup, 'property', 'og:locale', 'de_DE' if lang == 'de' else 'en_GB')
    meta(soup, 'property', 'og:url', f"{BASE}/{PAGES[page]['path'][lang]}")
    meta(soup, 'property', 'og:image', OG_IMAGE)
    for l in soup.select('link[rel="canonical"], link[rel="alternate"]'): l.decompose()
    def link(rel_, href, hreflang=None):
        t = soup.new_tag('link'); t['rel'] = rel_
        if hreflang: t['hreflang'] = hreflang
        t['href'] = href; soup.head.append(t)
    link('canonical', f"{BASE}/{PAGES[page]['path'][lang]}")
    link('alternate', f"{BASE}/{PAGES[page]['path']['de']}", 'de')
    link('alternate', f"{BASE}/{PAGES[page]['path']['en']}", 'en')
    link('alternate', f"{BASE}/{PAGES[page]['path']['de']}", 'x-default')

    if page == 'index':
        ld = {
            '@context': 'https://schema.org', '@type': 'BeautySalon',
            'name': 'Solvata Beauty Club Berlin', 'url': f"{BASE}/{PAGES[page]['path'][lang]}",
            'image': OG_IMAGE, 'telephone': '+49 176 80880879',
            'address': {'@type': 'PostalAddress', 'streetAddress': 'Berliner Straße 54', 'postalCode': '10713',
                        'addressLocality': 'Berlin', 'addressCountry': 'DE'},
            'openingHoursSpecification': [{'@type': 'OpeningHoursSpecification',
                                           'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
                                           'opens': '10:00', 'closes': '20:00'}],
            'sameAs': ['https://www.instagram.com/solvatabeautyclub'],
        }
        s = soup.new_tag('script'); s['type'] = 'application/ld+json'
        s.string = json.dumps(ld, ensure_ascii=False)
        soup.head.append(s)

    # internal links
    if lang == 'en':
        for a in soup.select('a[href]'):
            h = a['href']
            base, _, frag = h.partition('#')
            if base in LINK_MAP:
                a['href'] = LINK_MAP[base] + ('#' + frag if frag else '')

    # language switcher = plain links
    for sw in soup.select('.lang-switcher'):
        sw.clear()
        for code, label in (('de', 'DE'), ('en', 'EN')):
            a = soup.new_tag('a'); a['class'] = ['lang-btn'] + (['active'] if code == lang else [])
            a['href'] = rel(lang, page, code); a['hreflang'] = code; a['lang'] = code
            a.string = label
            sw.append(a)

    out = os.path.join(OUT, PAGES[page]['path'][lang])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write('<!DOCTYPE html>\n' + str(soup.html) + '\n')
    return out

if __name__ == '__main__':
    for p in PAGES:
        for l in ('de', 'en'):
            print('built', build(p, l))
    urls = [f"{BASE}/{PAGES[p]['path'][l]}" for p in PAGES for l in ('de', 'en')]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for p in PAGES:
        for l in ('de', 'en'):
            sm.append(f"  <url><loc>{BASE}/{PAGES[p]['path'][l]}</loc>")
            for l2 in ('de', 'en'):
                sm.append(f'    <xhtml:link rel="alternate" hreflang="{l2}" href="{BASE}/{PAGES[p]["path"][l2]}"/>')
            sm.append('  </url>')
    sm.append('</urlset>')
    open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write('\n'.join(sm) + '\n')
    print('built sitemap.xml')
