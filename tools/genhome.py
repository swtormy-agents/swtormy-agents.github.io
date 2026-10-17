import os,re
D='/workspace/swtormy-agents.github.io'; S='https://noclaudkit.com/'
CSP="default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'"
I={'logo':'<svg viewBox="0 0 28 28" aria-hidden="true"><rect x="1" y="1" width="26" height="26" rx="7" fill="currentColor"/><path d="M8 19V9l12 10V9" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
'conv':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="11" height="11" rx="2"/><path d="m3 12 3-3 4 4"/><path d="M17 9h3v11H9v-3"/><path d="m15 18 2 2 2-2"/></svg>',
'comp':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v6m-3-3 3 3 3-3M12 21v-6m-3 3 3-3 3 3M4 12h16"/></svg>',
'res':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="9" width="12" height="12" rx="2"/><path d="M14 3h7v7M21 3l-8 8"/></svg>',
'b':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/></svg>',
'u':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 18a4 4 0 0 1-.5-8A6 6 0 0 1 18 9a4 4 0 0 1 0 9"/><path d="M4 4l16 16"/></svg>',
'f':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>'}
NB='\u00a0'
# copy: /workspace/design/noclaudkit-home/copy-review.md (verbatim; ru short-word U+00A0 via nb())
L={
'en':dict(p='',hl='en',title='NoClaudKit — browser tools, files never leave your device',desc='Free image tools that run entirely in your browser. Files are not uploaded to a server and never leave your device. No sign-up.',og='en_US',h1=f'Small tools for{NB}everyday files',lead='Tools that run in your browser. Files never leave your device.',cta='Convert images',conv='/image-converter/',tools='Tools',ct='Image converter',cd='HEIC, WebP, AVIF, PNG and JPEG to JPEG, PNG or WebP.',mt='',
 soon='Coming soon',c2='Compress images',c2d='Make image files smaller.',c3='Resize images',c3d='Change image dimensions.',fh='How it works',f=[('Runs in your browser','Processing happens on your device.'),('No upload','Files are not sent to a server.'),('Free','No account needed.')],nav='Language',skip='Skip to content',nf='Page not found',nfb='Go to the home page',legal='Not affiliated with or endorsed by any device, browser or software maker; format names are used descriptively.'),
'ru':dict(p='ru/',hl='ru',title='NoClaudKit — инструменты прямо в браузере',desc='Бесплатные инструменты для изображений работают в вашем браузере: файлы не отправляются на сервер и не покидают устройство. Без регистрации.',og='ru_RU',h1='Простые инструменты для файлов',lead='Инструменты работают в вашем браузере: файлы не отправляются на сервер и не покидают устройство.',cta='Конвертировать изображения',conv='/image-converter/ru/',tools='Инструменты',ct='Конвертер изображений',cd='HEIC, WebP, AVIF, PNG и JPEG в JPEG, PNG или WebP.',mt='',
 soon='Скоро',c2='Сжатие изображений',c2d='Уменьшает размер файлов.',c3='Изменение размера',c3d='Меняет ширину и высоту изображения.',fh='Как это работает',f=[('Работает в браузере','Обработка идёт на вашем устройстве.'),('Без загрузки на сервер','Файлы не отправляются на сервер.'),('Бесплатно','Регистрация не нужна.')],nav='Язык',skip='Перейти к содержанию',nf='Страница не найдена',nfb='На главную',legal='Сайт не связан с производителями устройств, браузеров и программ и не одобрен ими; названия форматов используются для описания.'),
'zh':dict(p='zh/',hl='zh-Hans',title='NoClaudKit — 在浏览器中本地运行的工具',desc='免费图片工具，完全在浏览器中本地运行。文件不会上传到服务器，也不会离开您的设备。无需注册。',og='zh_CN',h1='处理日常文件的小工具',lead='全部工具均在您的浏览器中本地运行，文件不会上传到服务器。',cta='转换图片',conv='/image-converter/zh/',tools='工具',ct='图片转换器',cd='将 HEIC、WebP、AVIF、PNG 和 JPEG 转换为 JPEG、PNG 或 WebP。',mt='机器翻译，可能存在不准确之处。',
 soon='即将推出',c2='图片压缩',c2d='减小图片文件大小。',c3='调整图片尺寸',c3d='更改图片的宽度和高度。',fh='工作方式',f=[('在浏览器中运行','在您的设备上完成处理。'),('不上传','文件不会上传到服务器。'),('免费','无需注册账号。')],nav='语言',skip='跳到主要内容',nf='页面未找到',nfb='返回首页',legal='本站与任何设备、浏览器或软件厂商无关，亦未获其认可；格式名称仅用于描述。')}
SW='не и с в на к о у а из за по от до'.split()
def nb(t): return re.sub(r'(?<![\w\u0400-\u04FF])('+'|'.join(SW)+r') (?=\S)',lambda m:m.group(1)+NB,t,flags=re.I)
def fix(v):
  if isinstance(v,str): return nb(v)
  if isinstance(v,list): return [tuple(nb(x) for x in p) for p in v]
  return v
L['ru']={k:(fix(v) if k not in('p','hl','conv','og') else v) for k,v in L['ru'].items()}
NAMES={'en':'English','ru':'Русский','zh':'中文'}
TC='<meta name="theme-color" content="#f4f5f8" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#10131a" media="(prefers-color-scheme: dark)">'
def head(l,title,canon,alts=True,css='/home.css',extra='',desc=None):
  a=''.join(f'<link rel="alternate" hreflang="{L[k]["hl"]}" href="{S}{L[k]["p"]}">' for k in L)+f'<link rel="alternate" hreflang="x-default" href="{S}">' if alts else ''
  c=f'<link rel="canonical" href="{canon}">' if canon else '<meta name="robots" content="noindex">'
  return f'<!doctype html>\n<html lang="{L[l]["hl"]}"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{CSP}"><meta name="referrer" content="no-referrer"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><meta name="description" content="{desc or L[l]["lead"]}">{extra}{c}{a}<link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="{css}"></head>'.replace('\u00a0',' ')  # U+00A0 only in visible text, never in head/attributes
def nav(l):
  return '<nav aria-label="Language"><ul>'+''.join(f'<li><a href="/{L[k]["p"]}" lang="{L[k]["hl"]}" hreflang="{L[k]["hl"]}"'+(' aria-current="page"' if k==l else '')+f'>{NAMES[k]}</a></li>' for k in L)+'</ul></nav>'
# Counsel condition: "Coming soon" cards have NO links (no <a>, no href, no tabindex)
def soon(d,t,ds,ic): return f'<li><div class="card soon"><span class="ico">{I[ic]}</span><div><h3>{t}</h3><p>{ds}</p><span class="tag">{d["soon"]}</span></div></div></li>'
for k,d in L.items():
  os.makedirs(f'{D}/{d["p"]}',exist_ok=True)
  mt=f'<div class="mt" role="note"><div class="wrap"><span>{d["mt"]}</span><a href="/" lang="en" hreflang="en">Read in English</a></div></div>' if d['mt'] else ''
  langs=''.join(f'<li><a href="/{L[kk]["p"]}" lang="{L[kk]["hl"]}" hreflang="{L[kk]["hl"]}"'+(' aria-current="page"' if kk==k else '')+f'>{NAMES[kk]}</a></li>' for kk in L)
  facts=''.join(f'<li>{I[ic]}<div><strong>{a}</strong><span>{b}</span></div></li>' for ic,(a,b) in zip('buf',d['f']))
  og=f'<meta property="og:type" content="website"><meta property="og:url" content="{S}{d["p"]}"><meta property="og:title" content="{d["title"]}"><meta property="og:description" content="{d["desc"]}"><meta property="og:locale" content="{d["og"]}">'+''.join(f'<meta property="og:locale:alternate" content="{L[kk]["og"]}">' for kk in L if kk!=k)
  h=(head(k,d['title'],S+d['p'],css='/home.css',extra=TC+og,desc=d['desc'])
   +f'\n<body><a class="skip" href="#main">{d["skip"]}</a>{mt}<header><div class="wrap"><a class="brand" href="/{d["p"]}">{I["logo"]}<span translate="no">NoClaudKit</span></a><nav aria-label="{d["nav"]}"><ul class="langs">{langs}</ul></nav></div></header>\n'
   +f'<main id="main" tabindex="-1"><section class="hero wrap"><h1>{d["h1"]}</h1><p>{d["lead"]}</p><a class="btn" href="{d["conv"]}">{d["cta"]}</a></section>\n'
   +f'<section class="tools wrap" aria-labelledby="t"><h2 id="t">{d["tools"]}</h2><ul class="grid">\n'
   +f'<li><div class="card live"><span class="ico">{I["conv"]}</span><div><h3><a href="{d["conv"]}">{d["ct"]}</a></h3><p>{d["cd"]}</p></div></div></li>\n'
   +soon(d,d["c2"],d["c2d"],"comp")+soon(d,d["c3"],d["c3d"],"res")+'</ul></section>\n'
   +f'<section class="facts" aria-labelledby="f"><div class="wrap"><h2 id="f">{d["fh"]}</h2><ul>{facts}</ul></div></section></main>\n'
   +f'<footer><div class="wrap"><span translate="no">NoClaudKit</span><p>{d["legal"]}</p></div></footer></body></html>\n')
  open(f'{D}/{d["p"]}index.html','w').write(h)
x=L['en'];r=L['ru'];z=L['zh']
langs404=''.join(f'<li><a href="/{L[k]["p"]}" lang="{L[k]["hl"]}" hreflang="{L[k]["hl"]}">{NAMES[k]}</a></li>' for k in L)
open(f'{D}/404.html','w').write(head('en','404 — NoClaudKit',None,False,css='/home.css',extra=TC)+f'\n<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap"><a class="brand" href="/">{I["logo"]}<span translate="no">NoClaudKit</span></a><nav aria-label="Language"><ul class="langs">{langs404}</ul></nav></div></header>\n<main id="main" tabindex="-1"><section class="hero wrap nf"><h1>404</h1><p lang="en">{x["nf"]}. <a href="/">{x["nfb"]}</a></p><p lang="ru">{r["nf"]}. <a href="/ru/">{r["nfb"]}</a></p><p lang="zh-Hans">{z["nf"]}。<a href="/zh/">{z["nfb"]}</a></p></section></main>\n<footer><div class="wrap"><span translate="no">NoClaudKit</span></div></footer></body></html>\n')
open(f'{D}/CNAME','w').write('noclaudkit.com\n')
open(f'{D}/.nojekyll','w').write('')
open(f'{D}/robots.txt','w').write('User-agent: *\nAllow: /\nSitemap: https://noclaudkit.com/sitemap.xml\n')
open(f'{D}/sitemap.xml','w').write(f'<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n<sitemap><loc>{S}sitemap-home.xml</loc></sitemap>\n<sitemap><loc>{S}image-converter/sitemap.xml</loc></sitemap>\n</sitemapindex>\n')
alts=''.join(f'<xhtml:link rel="alternate" hreflang="{L[k]["hl"]}" href="{S}{L[k]["p"]}"/>' for k in L)+f'<xhtml:link rel="alternate" hreflang="x-default" href="{S}"/>'
open(f'{D}/sitemap-home.xml','w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'+''.join(f'<url><loc>{S}{L[k]["p"]}</loc>{alts}</url>\n' for k in L)+'</urlset>\n')
# redirect stubs
sm=open('/workspace/local-image-converter/sitemap.xml').read()
old='https://swtormy-agents.github.io/local-image-converter/'
paths=[re.sub(r'^https://(swtormy-agents\.github\.io/local-image-converter|noclaudkit\.com/image-converter)/','',u) for u in re.findall(r'<loc>([^<]*)',sm)]
for p in paths:
  f=f'{D}/local-image-converter/{p}'+('index.html' if p=='' or p.endswith('/') else '')
  os.makedirs(os.path.dirname(f),exist_ok=True)
  t=f'{S}image-converter/{p}'
  open(f,'w').write(f'<!doctype html>\n<html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{CSP}"><meta http-equiv="refresh" content="0; url={t}"><link rel="canonical" href="{t}"><title>Moved</title></head><body><p><a href="{t}">{t}</a></p></body></html>\n')
print(len(paths))
