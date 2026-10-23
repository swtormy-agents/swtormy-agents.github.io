// Home theme: loaded synchronously in <head> (CSP script-src 'self'), runs before first paint.
// Honours the choice saved by /pdf/ and /image-converter/: localStorage "lic-theme" = "light" | "dark"
// (absent = follow system). Same rule as the tools: on mobile (<=599px) the system theme always applies.
// Read-only here; never sent anywhere, no cookies.
(function(){
  var r=document.documentElement,m=window.matchMedia?window.matchMedia('(max-width: 599px)'):null;
  function v(){try{var t=window.localStorage.getItem('lic-theme');return t==='light'||t==='dark'?t:'';}catch(e){return '';}}
  function apply(){var t=(m&&m.matches)?'':v();
    if(t)r.setAttribute('data-theme',t==='dark'?'lagoon-dark':'lagoon');else r.removeAttribute('data-theme');}
  apply();
  if(m){if(m.addEventListener)m.addEventListener('change',apply);else if(m.addListener)m.addListener(apply);}
})();
