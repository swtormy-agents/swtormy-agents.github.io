import os,re
D='/workspace/swtormy-agents.github.io'; S='https://noclaudkit.com/'
CSP="default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'"
L={'en':dict(p='',hl='en',t='NoClaudKit — private browser tools',h='NoClaudKit',d='Privacy-first tools that run entirely in your browser. Your files are never uploaded.',s='Tools',n='Image converter',nd='HEIC, WebP, AVIF, PNG and JPG conversion on your device.',u='image-converter/',nf='Page not found',nfb='Go to the home page'),
'ru':dict(p='ru/',hl='ru',t='NoClaudKit — инструменты, которые работают в\u00a0браузере',h='NoClaudKit',d='Инструменты работают в вашем браузере: файлы не отправляются на сервер и не покидают устройство.',s='Инструменты',n='Конвертер изображений',nd='HEIC, WebP, AVIF, PNG и\u00a0JPG — конвертация на\u00a0вашем устройстве.',u='image-converter/ru/',nf='Страница не\u00a0найдена',nfb='На главную'),
'zh':dict(p='zh/',hl='zh-Hans',t='NoClaudKit — 在浏览器中本地运行的工具',h='NoClaudKit',d='全部工具均在您的浏览器中本地运行，文件不会上传到服务器。',s='工具',n='图片格式转换器',nd='在您的设备上转换 HEIC、WebP、AVIF、PNG 和 JPG。',u='image-converter/zh/',nf='页面未找到',nfb='返回首页')}
NAMES={'en':'English','ru':'Русский','zh':'中文'}
def head(l,title,canon,alts=True):
  a=''.join(f'<link rel="alternate" hreflang="{L[k]["hl"]}" href="{S}{L[k]["p"]}">' for k in L)+f'<link rel="alternate" hreflang="x-default" href="{S}">' if alts else ''
  c=f'<link rel="canonical" href="{canon}">' if canon else '<meta name="robots" content="noindex">'
  return f'<!doctype html>\n<html lang="{L[l]["hl"]}"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{CSP}"><meta name="referrer" content="no-referrer"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><meta name="description" content="{L[l]["d"]}">{c}{a}<link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/style.css"></head><body>'
def nav(l):
  return '<nav aria-label="Language"><ul>'+''.join(f'<li><a href="/{L[k]["p"]}" lang="{L[k]["hl"]}" hreflang="{L[k]["hl"]}"'+(' aria-current="page"' if k==l else '')+f'>{NAMES[k]}</a></li>' for k in L)+'</ul></nav>'
for l,x in L.items():
  os.makedirs(f'{D}/{x["p"]}',exist_ok=True)
  open(f'{D}/{x["p"]}index.html','w').write(head(l,x['t'],S+x['p'])+f'<header><a class="brand" href="/{x["p"]}">NoClaudKit</a>{nav(l)}</header><main>{'<p class="mt-notice" role="note">机器翻译，可能存在不准确之处。<a href="/" lang="en" hreflang="en">English</a></p>' if l=='zh' else ''}<h1>{x["h"]}</h1><p class="lead">{x["d"]}</p><h2>{x["s"]}</h2><ul class="tools"><li><a href="/{x["u"]}">{x["n"]}</a><p>{x["nd"]}</p></li></ul></main></body></html>\n')
x=L['en'];r=L['ru'];z=L['zh']
open(f'{D}/404.html','w').write(head('en','404 — NoClaudKit',None,False)+f'<header><a class="brand" href="/">NoClaudKit</a>{nav(None)}</header><main><h1>404</h1><p lang="en">{x["nf"]}. <a href="/">{x["nfb"]}</a></p><p lang="ru">{r["nf"]}. <a href="/ru/">{r["nfb"]}</a></p><p lang="zh-Hans">{z["nf"]}。<a href="/zh/">{z["nfb"]}</a></p></main></body></html>\n')
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
