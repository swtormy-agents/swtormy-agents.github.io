import html as htmlmod,json,os,re,subprocess,sys
from html.parser import HTMLParser
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S='https://noclaudkit.com/'
SEO_PATH=f'{D}/tools/i18n/home-seo.json'
SEO_FIELDS=('title','desc','h1','editorial_html')
PH_RE=re.compile(r'\b(?:TODO|lorem|placeholder|TBD)\b',re.I)
FORBIDDEN_MARKUP_RE=re.compile(r'<[?!]',re.I)
ALLOWED_ED_TAGS=frozenset('p ul ol li strong em a'.split())
ROOT_TAGS=frozenset('p ul ol'.split())
INLINE_TAGS=frozenset('a strong em'.split())
ALLOWED_CHILD={None:ROOT_TAGS,'p':INLINE_TAGS,'ul':frozenset('li'),'ol':frozenset('li'),
  'li':ROOT_TAGS|INLINE_TAGS,'strong':INLINE_TAGS,'em':INLINE_TAGS,'a':frozenset(('strong','em'))}
REL_HREF_RE=re.compile(r'^/[a-z0-9\-/._#]*$')
def esc(s): return htmlmod.escape(s,quote=True)
def hero_h1(s): return f'<h1>{esc(s)}</h1>'
def valid_rel_href(raw):
  h=htmlmod.unescape(raw)
  if not h.startswith('/') or h.startswith('//') or '\\' in h: return False
  if any(ord(c)<32 or c.isspace() for c in h): return False
  if ':' in h[1:]: return False
  return bool(REL_HREF_RE.match(h))
CSP="default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'"
I={'logo':'<svg viewBox="0 0 28 28" aria-hidden="true"><rect x="1" y="1" width="26" height="26" rx="7" fill="currentColor"/><path d="M8 19V9l12 10V9" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
'conv':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="11" height="11" rx="2"/><path d="m3 12 3-3 4 4"/><path d="M17 9h3v11H9v-3"/><path d="m15 18 2 2 2-2"/></svg>',
'comp':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v6m-3-3 3 3 3-3M12 21v-6m-3 3 3-3 3 3M4 12h16"/></svg>',
'res':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="9" width="12" height="12" rx="2"/><path d="M14 3h7v7M21 3l-8 8"/></svg>',
'b':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/></svg>',
'u':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 18a4 4 0 0 1-.5-8A6 6 0 0 1 18 9a4 4 0 0 1 0 9"/><path d="M4 4l16 16"/></svg>',
'pdf':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h8l5 5v13H6z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/></svg>',
'f':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>'}
NB='\u00a0'
# copy: /workspace/design/noclaudkit-home/copy-review.md (verbatim; ru short-word U+00A0 via nb())
L={
'en':dict(p='',hl='en',og='en_US',lead='Tools that run in your browser. Files never leave your device.',cta='Convert images',conv='/image-converter/',tools='Tools',ct='Image converter',cd='HEIC, WebP, AVIF, PNG and JPEG to JPEG, PNG or WebP.',pt='PDF tools',pd='Merge and split PDF files, reorder pages, turn images into PDF.',pdf='/pdf/',mt='',
 soon='Coming soon',c2='Compress images',c2d='Make image files smaller.',c3='Resize images',c3d='Change image dimensions.',fh='How it works',f=[('Runs in your browser','Processing happens on your device.'),('No upload','Files are not sent to a server.'),('Free','No account needed.')],nav='Language',skip='Skip to content',nf='Page not found',nfb='Go to the home page',legal='Not affiliated with or endorsed by any device, browser or software maker; format names are used descriptively.'),
'ru':dict(p='ru/',hl='ru',og='ru_RU',lead='Инструменты работают в вашем браузере: файлы не отправляются на сервер и не покидают устройство.',cta='Конвертировать изображения',conv='/image-converter/ru/',tools='Инструменты',ct='Конвертер изображений',cd='HEIC, WebP, AVIF, PNG и JPEG в JPEG, PNG или WebP.',pt='Инструменты для PDF',pd='Объединение и разделение PDF, изменение порядка страниц, PDF из изображений.',pdf='/pdf/ru/',mt='',
 soon='Скоро',c2='Сжатие изображений',c2d='Уменьшает размер файлов.',c3='Изменение размера',c3d='Меняет ширину и высоту изображения.',fh='Как это работает',f=[('Работает в браузере','Обработка идёт на вашем устройстве.'),('Без загрузки на сервер','Файлы не отправляются на сервер.'),('Бесплатно','Регистрация не нужна.')],nav='Язык',skip='Перейти к содержанию',nf='Страница не найдена',nfb='На главную',legal='Сайт не связан с производителями устройств, браузеров и программ и не одобрен ими; названия форматов используются для описания.'),
'zh':dict(p='zh/',hl='zh-Hans',og='zh_CN',lead='全部工具均在您的浏览器中本地运行，文件不会上传到服务器。',cta='转换图片',conv='/image-converter/zh/',tools='工具',ct='图片转换器',cd='将 HEIC、WebP、AVIF、PNG 和 JPEG 转换为 JPEG、PNG 或 WebP。',pt='PDF 工具',pd='合并、拆分 PDF，调整页面顺序，图片转 PDF。',pdf='/pdf/zh/',mt='机器翻译，可能存在不准确之处。',
 soon='即将推出',c2='图片压缩',c2d='减小图片文件大小。',c3='调整图片尺寸',c3d='更改图片的宽度和高度。',fh='工作方式',f=[('在浏览器中运行','在您的设备上完成处理。'),('不上传','文件不会上传到服务器。'),('免费','无需注册账号。')],nav='语言',skip='跳到主要内容',nf='页面未找到',nfb='返回首页',legal='本站与任何设备、浏览器或软件厂商无关，亦未获其认可；格式名称仅用于描述。')}
SW='не и с в на к о у а из за по от до'.split()
def nb(t): return re.sub(r'(?<![\w\u0400-\u04FF])('+'|'.join(SW)+r') (?=\S)',lambda m:m.group(1)+NB,t,flags=re.I)
def fix(v):
  if isinstance(v,str): return nb(v)
  if isinstance(v,list): return [tuple(nb(x) for x in p) for p in v]
  return v
L['ru']={k:(fix(v) if k not in('p','hl','conv','og','pdf') else v) for k,v in L['ru'].items()}
_OPEN_SIMPLE=('p','ul','ol','li','strong','em')
_CLOSE_TAGS=('p','ul','ol','li','strong','em','a')
_A_OPEN='<a href="'
def _tok_parent(stack): return stack[-1] if stack else None
def _tok_allowed(par,tag):
  allowed=ALLOWED_CHILD[None] if par is None else ALLOWED_CHILD.get(par)
  return allowed is not None and tag in allowed
def _tokenizer_validate(s):
  stack=[]; pos=0; n=len(s)
  while pos<n:
    if s[pos]!='<':
      if s[pos]=='>': return [f'stray > at {pos}']
      while pos<n and s[pos] not in '<>': pos+=1
      continue
    matched=False
    for tag in _CLOSE_TAGS:
      tok=f'</{tag}>'
      if s.startswith(tok,pos):
        if not stack or stack[-1]!=tag: return [f'mismatched end tag </{tag}> at {pos}']
        stack.pop(); pos+=len(tok); matched=True; break
    if matched: continue
    for tag in _OPEN_SIMPLE:
      tok=f'<{tag}>'
      if s.startswith(tok,pos):
        par=_tok_parent(stack)
        if not _tok_allowed(par,tag): return [f'<{tag}> not allowed inside <{par}> at {pos}']
        stack.append(tag); pos+=len(tok); matched=True; break
    if matched: continue
    if s.startswith(_A_OPEN,pos):
      par=_tok_parent(stack)
      if not _tok_allowed(par,'a'): return [f'<a> not allowed inside <{par}> at {pos}']
      pos+=len(_A_OPEN)
      q=pos
      while q<n and s[q]!='"': q+=1
      if q>=n: return ['unterminated href string']
      href=s[pos:q]
      if not valid_rel_href(href): return [f'a href not allowed: {href!r}']
      if q+1>=n or s[q+1]!='>': return ['a tag must be exactly <a href="...">']
      pos=q+2; stack.append('a'); continue
    return [f'invalid token at {pos}: {s[pos:pos+40]!r}']
  if stack: return ['unclosed tags: '+', '.join(stack)]
  return []
class _EdGuard(HTMLParser):
  def __init__(self): super().__init__(); self.err=[]; self.stack=[]
  def _parent(self): return self.stack[-1] if self.stack else None
  def handle_starttag(self,tag,attrs):
    t=tag.lower()
    if t not in ALLOWED_ED_TAGS: self.err.append(f'unallowed tag <{t}>'); return
    if attrs:
      if t=='a':
        if len(attrs)!=1 or attrs[0][0].lower()!='href': self.err.append('a must have only href attribute')
        elif not valid_rel_href(attrs[0][1]): self.err.append(f'a href not allowed: {attrs[0][1]!r}')
      else: self.err.append(f'<{t}> must not have attributes')
    elif t=='a': self.err.append('a without href')
    par=self._parent()
    allowed=ALLOWED_CHILD[None] if par is None else ALLOWED_CHILD.get(par)
    if allowed is None or t not in allowed: self.err.append(f'<{t}> not allowed inside <{par}>')
    self.stack.append(t)
  def handle_endtag(self,tag):
    t=tag.lower()
    if t not in ALLOWED_ED_TAGS: self.err.append(f'unallowed end tag </{t}>'); return
    if not self.stack or self.stack[-1]!=t:
      self.err.append(f'mismatched end tag </{t}>'); return
    self.stack.pop()
  def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs)
  def handle_comment(self,data): self.err.append('comments not allowed')
  def handle_decl(self,decl): self.err.append(f'declaration not allowed: {decl!r}')
  def handle_pi(self,data): self.err.append(f'processing instruction not allowed: {data!r}')
  def unknown_decl(self,data): self.err.append(f'unknown declaration not allowed: {data!r}')
  def close(self):
    super().close()
    if self.stack: self.err.append('unclosed tags: '+', '.join(self.stack))
def validate_editorial_html(html):
  if FORBIDDEN_MARKUP_RE.search(html): return ['forbidden markup (<! or <?)']
  err=_tokenizer_validate(html)
  if err: return err
  g=_EdGuard(); g.feed(html); g.close()
  return g.err
def load_seo():
  seo=json.load(open(SEO_PATH,encoding='utf-8'))
  for lang in L:
    home=seo.get(lang,{}).get('home')
    if not home: sys.exit(f'genhome: {lang}.home missing in {SEO_PATH}')
    for f in SEO_FIELDS:
      v=home.get(f)
      if v is None or (isinstance(v,str) and not v.strip()): sys.exit(f'genhome: {lang}.home.{f} missing or empty')
      if PH_RE.search(str(v)): sys.exit(f'genhome: {lang}.home.{f} contains placeholder marker')
    err=validate_editorial_html(home['editorial_html'])
    if err: sys.exit(f'genhome: {lang}.home.editorial_html invalid: {"; ".join(err)}')
    L[lang]['title']=home['title']
    L[lang]['desc']=home['desc']
    L[lang]['h1']=nb(home['h1']) if lang=='ru' else home['h1']
    L[lang]['editorial_html']=nb(home['editorial_html']) if lang=='ru' else home['editorial_html']
IL=json.load(open(f'{D}/tools/i18n/interlink.json',encoding='utf-8'))
NAMES={'en':'English','ru':'Русский','zh':'中文'}
FT_KEYS=('home','conv','pdf','heic','merge','split','jpg')
FT_LABEL={'home':'ft_home','conv':'f_conv','pdf':'f_pdf','heic':'ft_heic','merge':'ft_merge','split':'ft_split','jpg':'ft_jpg'}
POP_CONV=[('heic-to-jpg.html','ft_heic'),('heic-to-png.html','ft_heic_png'),('webp-to-png.html','ft_webp_png'),('webp-to-jpg.html','ft_webp_jpg'),('avif-to-jpg.html','ft_avif_jpg'),('avif-to-png.html','ft_avif_png'),('png-to-webp.html','ft_png_webp'),('jpg-to-webp.html','ft_jpg_webp')]
POP_PDF=[('merge-pdf.html','ft_merge'),('split-pdf.html','ft_split'),('organize-pdf.html','ft_organize'),('jpg-to-pdf.html','ft_jpg')]
def loc(l): return '' if l=='en' else l+'/'
def vis(l,s): return nb(s) if l=='ru' else s
def tool_href(l,section,slug):
  return f'/{section}/{loc(l)}{slug}'
def ft_href(l,key):
  p=loc(l)
  return {'home':f'/{p}','conv':f'/image-converter/{p}','pdf':f'/pdf/{p}',
          'heic':f'/image-converter/{p}heic-to-jpg.html',
          'merge':f'/pdf/{p}merge-pdf.html','split':f'/pdf/{p}split-pdf.html',
          'jpg':f'/pdf/{p}jpg-to-pdf.html'}[key]
def pop_html(l,pairs,section):
  t=IL[l]
  return '<ul class="pop">'+''.join(f'<li><a href="{tool_href(l,section,slug)}">{vis(l,t[ilkey])}</a></li>' for slug,ilkey in pairs)+'</ul>'
def ensure_git_history():
  r=subprocess.run(['git','rev-parse','--is-shallow-repository'],capture_output=True,text=True,cwd=D)
  if r.returncode: sys.exit('genhome: cannot determine whether git checkout is shallow')
  if r.stdout.strip()!='true': return
  env={**os.environ,'GIT_TERMINAL_PROMPT':'0'}
  try:
    fr=subprocess.run(['git','fetch','--unshallow'],capture_output=True,text=True,cwd=D,env=env,timeout=180)
  except subprocess.TimeoutExpired:
    sys.exit('genhome: git fetch --unshallow timed out; cannot compute lastmod')
  if fr.returncode: sys.exit('genhome: git fetch --unshallow failed: '+(fr.stderr or fr.stdout).strip())
def git_lastmod(rel):
  r=subprocess.run(['git','log','-1','--format=%cs','--',rel],capture_output=True,text=True,cwd=D)
  d=r.stdout.strip()
  if not d: sys.exit(f'genhome: empty lastmod for {rel!r}; git history unavailable')
  return d
def home_lastmod(l):
  rel='index.html' if not L[l]['p'] else f'{L[l]["p"]}index.html'
  return git_lastmod(rel)
def ft_html(l):
  t=IL[l]; items=[]
  for key in FT_KEYS:
    items.append('<li><a href="'+ft_href(l,key)+'"'+(' translate="no"' if key=='home' else '')
                 +(' aria-current="page"' if key=='home' else '')+'>'+vis(l,t[FT_LABEL[key]])+'</a></li>')
  return f'<nav class="ft" aria-labelledby="ft-h"><h2 id="ft-h">{vis(l,t["ft_all"])}</h2><ul>'+''.join(items)+'</ul></nav>'
TC='<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0b1d20" media="(prefers-color-scheme: dark)">'
def head(l,title,canon,alts=True,css='/home.css',extra='',desc=None):
  a=''.join(f'<link rel="alternate" hreflang="{L[k]["hl"]}" href="{S}{L[k]["p"]}">' for k in L)+f'<link rel="alternate" hreflang="x-default" href="{S}">' if alts else ''
  c=f'<link rel="canonical" href="{canon}">' if canon else '<meta name="robots" content="noindex">'
  dct=desc or L[l]['lead']
  return f'<!doctype html>\n<html lang="{L[l]["hl"]}"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{CSP}"><meta name="referrer" content="no-referrer"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(dct)}">{extra}{c}{a}<link rel="icon" href="/favicon.svg"><script src="/theme.js"></script><link rel="stylesheet" href="{css}"></head>'.replace('\u00a0',' ')  # U+00A0 only in visible text, never in head/attributes
def nav(l):
  return '<nav aria-label="Language"><ul>'+''.join(f'<li><a href="/{L[k]["p"]}" lang="{L[k]["hl"]}" hreflang="{L[k]["hl"]}"'+(' aria-current="page"' if k==l else '')+f'>{NAMES[k]}</a></li>' for k in L)+'</ul></nav>'
# Counsel condition: "Coming soon" cards have NO links (no <a>, no href, no tabindex)
def soon(d,t,ds,ic): return f'<li><div class="card soon"><span class="ico">{I[ic]}</span><div><h3>{t}</h3><p>{ds}</p><span class="tag">{d["soon"]}</span></div></div></li>'
def main():
  ensure_git_history()
  load_seo()
  for k,d in L.items():
    os.makedirs(f'{D}/{d["p"]}',exist_ok=True)
    mt=f'<div class="mt" role="note"><div class="wrap"><span>{d["mt"]}</span><a href="/" lang="en" hreflang="en">Read in English</a></div></div>' if d['mt'] else ''
    langs=''.join(f'<li><a href="/{L[kk]["p"]}" lang="{L[kk]["hl"]}" hreflang="{L[kk]["hl"]}"'+(' aria-current="page"' if kk==k else '')+f'>{NAMES[kk]}</a></li>' for kk in L)
    facts=''.join(f'<li>{I[ic]}<div><strong>{a}</strong><span>{b}</span></div></li>' for ic,(a,b) in zip('buf',d['f']))
    og=(f'<meta property="og:type" content="website"><meta property="og:url" content="{S}{d["p"]}"><meta property="og:title" content="{esc(d["title"])}">'
        f'<meta property="og:description" content="{esc(d["desc"])}"><meta property="og:locale" content="{d["og"]}">'
        f'<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(d["title"])}">'
        f'<meta name="twitter:description" content="{esc(d["desc"])}">'
        +''.join(f'<meta property="og:locale:alternate" content="{L[kk]["og"]}">' for kk in L if kk!=k))
    h=(head(k,d['title'],S+d['p'],css='/home.css',extra=TC+og,desc=d['desc'])
     +f'\n<body><a class="skip" href="#main">{d["skip"]}</a>{mt}<header><div class="wrap"><a class="brand" href="/{d["p"]}">{I["logo"]}<span translate="no">NoClaudKit</span></a><nav aria-label="{d["nav"]}"><ul class="langs">{langs}</ul></nav></div></header>\n'
     +f'<main id="main" tabindex="-1"><section class="hero wrap">{hero_h1(d["h1"])}<p>{d["lead"]}</p><a class="btn" href="{d["conv"]}">{d["cta"]}</a></section>\n'
     +f'<section class="tools wrap" aria-labelledby="t"><h2 id="t">{d["tools"]}</h2><ul class="grid">\n'
     +f'<li><div class="card live"><span class="ico">{I["conv"]}</span><div><h3><a href="{d["conv"]}">{d["ct"]}</a></h3><p>{d["cd"]}</p>{pop_html(k,POP_CONV,"image-converter")}</div></div></li>\n'
     +f'<li><div class="card live"><span class="ico">{I["pdf"]}</span><div><h3><a href="{d["pdf"]}">{d["pt"]}</a></h3><p>{d["pd"]}</p>{pop_html(k,POP_PDF,"pdf")}</div></div></li>\n'
     +soon(d,d["c2"],d["c2d"],"comp")+soon(d,d["c3"],d["c3d"],"res")+'</ul></section>\n'
     +f'<section class="editorial wrap">{d["editorial_html"]}</section>\n'
     +f'<section class="facts" aria-labelledby="f"><div class="wrap"><h2 id="f">{d["fh"]}</h2><ul>{facts}</ul></div></section></main>\n'
     +f'<footer><div class="wrap">{ft_html(k)}<p>{d["legal"]}</p></div></footer></body></html>\n')
    open(f'{D}/{d["p"]}index.html','w').write(h)
  x=L['en'];r=L['ru'];z=L['zh']
  langs404=''.join(f'<li><a href="/{L[k]["p"]}" lang="{L[k]["hl"]}" hreflang="{L[k]["hl"]}">{NAMES[k]}</a></li>' for k in L)
  open(f'{D}/404.html','w').write(head('en','404 — NoClaudKit',None,False,css='/home.css',extra=TC)+f'\n<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap"><a class="brand" href="/">{I["logo"]}<span translate="no">NoClaudKit</span></a><nav aria-label="Language"><ul class="langs">{langs404}</ul></nav></div></header>\n<main id="main" tabindex="-1"><section class="hero wrap nf"><h1>404</h1><p lang="en">{x["nf"]}. <a href="/">{x["nfb"]}</a></p><p lang="ru">{r["nf"]}. <a href="/ru/">{r["nfb"]}</a></p><p lang="zh-Hans">{z["nf"]}。<a href="/zh/">{z["nfb"]}</a></p></section></main>\n<footer><div class="wrap"><span translate="no">NoClaudKit</span></div></footer></body></html>\n')
  open(f'{D}/CNAME','w').write('noclaudkit.com\n')
  open(f'{D}/.nojekyll','w').write('')
  open(f'{D}/robots.txt','w').write('User-agent: *\nAllow: /\nSitemap: https://noclaudkit.com/sitemap.xml\n')
  open(f'{D}/sitemap.xml','w').write(f'<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n<sitemap><loc>{S}sitemap-home.xml</loc></sitemap>\n<sitemap><loc>{S}image-converter/sitemap.xml</loc></sitemap>\n<sitemap><loc>{S}pdf/sitemap.xml</loc></sitemap>\n</sitemapindex>\n')
  alts=''.join(f'<xhtml:link rel="alternate" hreflang="{L[k]["hl"]}" href="{S}{L[k]["p"]}"/>' for k in L)+f'<xhtml:link rel="alternate" hreflang="x-default" href="{S}"/>'
  open(f'{D}/sitemap-home.xml','w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'+''.join(f'<url><loc>{S}{L[k]["p"]}</loc><lastmod>{home_lastmod(k)}</lastmod>{alts}</url>\n' for k in L)+'</urlset>\n')
  sm_path=os.path.join(D,'local-image-converter','sitemap.xml')
  if os.path.isfile(sm_path):
    sm=open(sm_path).read()
    paths=[re.sub(r'^https://(swtormy-agents\.github\.io/local-image-converter|noclaudkit\.com/image-converter)/','',u) for u in re.findall(r'<loc>([^<]*)',sm)]
    for p in paths:
      f=f'{D}/local-image-converter/{p}'+('index.html' if p=='' or p.endswith('/') else '')
      os.makedirs(os.path.dirname(f),exist_ok=True)
      t=f'{S}image-converter/{p}'
      open(f,'w').write(f'<!doctype html>\n<html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{CSP}"><meta http-equiv="refresh" content="0; url={t}"><link rel="canonical" href="{t}"><title>Moved</title></head><body><p><a href="{t}">{t}</a></p></body></html>\n')
    print(len(paths))
  else:
    print(0)
if __name__=='__main__': main()
