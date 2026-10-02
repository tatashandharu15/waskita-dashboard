(function () {
  'use strict';

  (function initThemeEarly() {
    try {
      var stored = null;
      try { stored = localStorage.getItem('theme'); } catch (_) {}
      var theme;
      if (stored === 'light' || stored === 'dark') {
        theme = stored;
      } else {
        var prefDark = false;
        try { prefDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches; } catch (_) {}
        theme = prefDark ? 'dark' : 'light';
      }
      document.documentElement.setAttribute('data-theme', theme);
      document.body.setAttribute('data-theme', theme);
    } catch (_) {
      document.documentElement.setAttribute('data-theme', 'light');
      document.body.setAttribute('data-theme', 'light');
    }
  })();

  function getTheme() {
    var t = null;
    try { t = (document.documentElement.getAttribute('data-theme') || document.body.getAttribute('data-theme') || 'light').toLowerCase(); } catch (_) {}
    return (t === 'dark') ? 'dark' : 'light';
  }

  function setTheme(theme, persist) {
    theme = (theme === 'dark') ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
    if (persist !== false) {
      try { localStorage.setItem('theme', theme); } catch (_) {}
    }
    try { window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: theme } })); } catch (_) {}
  }

  var WORDCLOUD_PALETTES = {
    light: [
      '#2563eb', '#059669', '#0891b2', '#7c3aed', '#be185d',
      '#b45309', '#15803d', '#1d4ed8', '#9333ea', '#c2410c',
      '#0f766e', '#4338ca', '#166534', '#854d0e', '#0e7490',
      '#9f1239', '#1e40af', '#4f46e5', '#16a34a', '#ca8a04'
    ],
    dark: [
      '#60a5fa', '#34d399', '#22d3ee', '#a78bfa', '#f472b6',
      '#fbbf24', '#4ade80', '#93c5fd', '#c084fc', '#fb923c',
      '#2dd4bf', '#818cf8', '#86efac', '#fcd34d', '#38bdf8',
      '#fb7185', '#a5b4fc', '#34d399', '#facc15', '#fca5a5'
    ]
  };

  var state = {
    analytics: null,
    activeSource: 'all'
  };

  var ICONS = {
    barChart2: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>',
    pieChart: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>',
    clock: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>',
    hash: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="9" x2="20" y2="9"></line><line x1="4" y1="15" x2="20" y2="15"></line><line x1="10" y1="3" x2="8" y2="21"></line><line x1="16" y1="3" x2="14" y2="21"></line></svg>',
    usersRound: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
    globe: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
    languages: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8h14"></path><path d="M5 12h14"></path><path d="M5 16h14"></path></svg>',
    activity: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>',
    alertTriangle: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    thumbUp: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>',
    target: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>',
    calendar: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
    users2: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
    sparkles: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.912 5.813h6.112l-4.943 3.587 1.887 5.813L12 14.626l-4.968 3.587 1.887-5.813L3.976 8.813h6.112z"></path></svg>',
    filter: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>',
    messageSquare: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>',
    radio: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2"></circle><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"></path></svg>',
    search: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
    chevronDown: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>',
    flag: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg>',
    zap: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>',
    heart: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>',
    smiley: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>',
    frown: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M16 16s-1.5-2-4-2-4 2-4 2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>',
    meh: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="8" y1="15" x2="16" y2="15"></line><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>',
    arrowTrendUp: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
    arrowTrendDown: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>',
    arrowRight: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>',
    share: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>',
    eye: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>',
    alertCircle: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></circle></svg>',
    refreshCw: '<svg class="icon-inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>'
  };

  function _brandLogoSVG(key, size) {
    size = size || 18;
    var s = Number(size) || 18;
    var vw = 24;
    var prefix = '<svg class="brand-logo" width="' + s + '" height="' + s + '" viewBox="0 0 ' + vw + ' ' + vw + '" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">';
    var suf = '</svg>';
    var k = String(key || '').toLowerCase().trim();
    switch (k) {
      case 'instagram':
      case 'ig':
        return prefix +
          '<defs><linearGradient id="ig-logo-grad" x1="0%" y1="100%" x2="100%" y2="0%"><stop offset="0%" stop-color="#FFDC80"/><stop offset="30%" stop-color="#FD1D1D"/><stop offset="60%" stop-color="#E1306C"/><stop offset="100%" stop-color="#833AB4"/></linearGradient></defs>' +
          '<rect x="2" y="2" width="20" height="20" rx="6" fill="url(#ig-logo-grad)"/>' +
          '<rect x="6.2" y="6.2" width="11.6" height="11.6" rx="3.2" fill="none" stroke="#ffffff" stroke-width="1.4"/>' +
          '<circle cx="12" cy="12" r="3" fill="none" stroke="#ffffff" stroke-width="1.4"/>' +
          '<circle cx="17.2" cy="6.8" r="1" fill="#ffffff"/>' +
          suf;
      case 'youtube':
      case 'yt':
        return prefix +
          '<rect x="1.5" y="5" width="21" height="14" rx="3.5" fill="#FF0000"/>' +
          '<path d="M9.9 9.3 16 12 9.9 14.7V9.3Z" fill="#ffffff"/>' +
          suf;
      case 'facebook':
      case 'fb':
        return prefix +
          '<circle cx="12" cy="12" r="11" fill="#1877F2"/>' +
          '<path d="M13.6 9.4h-1.4c-.7 0-1.1.3-1.1 1v1.2h2.5l-.3 2.5h-2.2v6.5h-2.5V14.1h-2.3v-2.5h2.3v-1.5c0-2 1.1-3.2 3-3.2.9 0 1.6.1 1.9.1l-.1 2.8Z" fill="#ffffff"/>' +
          suf;
      case 'tiktok':
      case 'tt':
        return prefix +
          '<path d="M15.6 2.4c-.7.7-1.6 1.1-2.6 1.2V12c0 2.3-1.9 4.2-4.2 4.2S4.6 14.3 4.6 12s1.9-4.2 4.2-4.2c.3 0 .6 0 .9.1v2.8c-.3-.1-.6-.1-.9-.1-1.3 0-2.3 1-2.3 2.3 0 1.3 1 2.3 2.3 2.3 1.3 0 2.3-1 2.3-2.3V7.8a6 6 0 0 0 3.9 1.4v-2.9a3.2 3.2 0 0 1-2.6-3.9h1.3Z" fill="#25F4EE"/>' +
          '<path d="M16.9 3.7a6.1 6.1 0 0 1-3.9 1.4 3.2 3.2 0 0 0 3.9-3.9c.7.7 1.2 1.6 1.2 2.6v12a4.2 4.2 0 0 1-4.2 4.2 4.2 4.2 0 0 1-4.2-4.2 4.2 4.2 0 0 1 .9-2.5v3.1c0 1.3 1 2.3 2.3 2.3s2.3-1 2.3-2.3V3.7Z" fill="#FE2C55"/>' +
          '<path d="M16.9 6.3a3.1 3.1 0 0 1-1.3-1.7A3.2 3.2 0 0 1 19.5 2.6c-.3 1-.9 1.9-1.7 2.5.3 0 .6.3.6.6V12c0 2.3-1.9 4.2-4.2 4.2S10 14.3 10 12V8.5c.3.1.6.1.9.1C13.3 8.6 15 9.8 15.6 12h1.3V6.3Z" fill="#000000"/>' +
          suf;
      case 'linkedin':
      case 'in':
        return prefix +
          '<rect x="1.5" y="1.5" width="21" height="21" rx="3.5" fill="#0A66C2"/>' +
          '<rect x="5.2" y="8.9" width="2.4" height="6.8" fill="#ffffff"/>' +
          '<circle cx="6.4" cy="6.9" r="1.3" fill="#ffffff"/>' +
          '<path d="M9.8 10h2.3v1c.4-.7 1.4-1.5 3-1.5 2.2 0 3 1.5 3 3.9v4.3h-2.4v-3.8c0-1 0-2.1-1.3-2.1s-1.5 1.1-1.5 2V15.7h-2.5V10Z" fill="#ffffff"/>' +
          suf;
      case 'reddit':
      case 'r':
        return prefix +
          '<circle cx="12" cy="13.3" r="8.5" fill="#FF4500"/>' +
          '<circle cx="8.9" cy="13.3" r="1" fill="#ffffff"/>' +
          '<circle cx="15.1" cy="13.3" r="1" fill="#ffffff"/>' +
          '<path d="M9.2 16.2c0-.4.3-.7.7-.7h4.1c.4 0 .7.3.7.7 0 .4-.3.7-.7.7h-4.1a.7.7 0 0 1-.7-.7Z" fill="#ffffff"/>' +
          '<circle cx="16.5" cy="8.8" r="1.3" fill="#FF4500"/>' +
          '<circle cx="16.5" cy="8.8" r=".7" fill="#ffffff"/>' +
          '<path d="M15.2 8.8c0-1.8-1.5-3.3-3.2-3.3-1.2 0-2.2.6-2.8 1.6-.3-.1-1-.2-2.2-.2-2.3 0-4.3 1.1-4.3 2.4 0 .9.7 1.7 1.7 2.2v.4c0 3 2.8 5.4 6.3 5.4s6.3-2.4 6.3-5.4v-.4c1-.5 1.6-1.3 1.6-2.2 0-1.3-1.7-2.4-3.4-2.4Z" fill="none" stroke="#FF4500" stroke-width="1" stroke-linejoin="round"/>' +
          suf;
      case 'bsky':
      case 'bluesky':
        return prefix +
          '<rect x="2" y="3" width="20" height="18" rx="5" fill="#0560FF"/>' +
          '<path d="M6.1 8.7c0-2 1.6-3.3 3-3.3 1.2 0 2.1.6 2.9 2.6.8-2 1.8-2.6 3-2.6 1.4 0 2.9 1.3 2.9 3.3 0 2.2-.7 4.4-4.3 5.4l.9 3-2.7-1.7-1.2-.8-1.2.8-2.7 1.7.9-3c-3.6-1-4.5-3.2-4.5-5.4Z" fill="#ffffff"/>' +
          suf;
      case 'news':
      case 'newspaper':
        return prefix +
          '<rect x="2.5" y="4" width="19" height="16" rx="1.8" fill="#475569"/>' +
          '<rect x="4.6" y="6.5" width="6.4" height="2.2" rx=".6" fill="#fef3c7"/>' +
          '<rect x="12.4" y="6.5" width="6.2" height="1" rx=".5" fill="#cbd5e1"/>' +
          '<rect x="12.4" y="8.1" width="5.4" height="1" rx=".5" fill="#cbd5e1"/>' +
          '<rect x="4.6" y="10.5" width="14" height="1" rx=".5" fill="#cbd5e1"/>' +
          '<rect x="4.6" y="12.4" width="10.5" height="1" rx=".5" fill="#cbd5e1"/>' +
          '<rect x="4.6" y="14.3" width="12.5" height="1" rx=".5" fill="#cbd5e1"/>' +
          '<path d="M15.2 10.8h3m-3 1.9h2.3" stroke="#fde68a" stroke-width="1.2" stroke-linecap="round"/>' +
          suf;
      case 'site':
      case 'website':
      case 'blog':
        return prefix +
          '<circle cx="12" cy="12" r="10.5" fill="#059669"/>' +
          '<circle cx="12" cy="12" r="10.5" fill="none" stroke="#065f46" stroke-width="1"/>' +
          '<ellipse cx="12" cy="12" rx="10.5" ry="3.5" fill="none" stroke="#bbf7d0" stroke-width="1"/>' +
          '<path d="M12 1.5V22.5" stroke="#bbf7d0" stroke-width="1"/>' +
          '<rect x="6.3" y="8.7" width="11.4" height="6.6" rx="1.2" fill="#ffffff"/>' +
          '<rect x="7.3" y="10" width="9.4" height="1" rx=".5" fill="#374151"/>' +
          '<rect x="7.3" y="11.7" width="6.8" height="1" rx=".5" fill="#9ca3af"/>' +
          '<rect x="7.3" y="13.2" width="8.3" height="1" rx=".5" fill="#9ca3af"/>' +
          suf;
      default:
        return prefix +
          '<rect x="2.5" y="4" width="19" height="16" rx="3" fill="#64748b"/>' +
          '<circle cx="12" cy="11" r="2.2" fill="#ffffff"/>' +
          '<path d="M7 17.4c.8-2 2.6-3.3 5-3.3s4.2 1.3 5 3.3" fill="none" stroke="#ffffff" stroke-width="1.2" stroke-linecap="round"/>' +
          suf;
    }
  }

  function getBrandLogo(source, size) {
    if (!source) return _brandLogoSVG('default', size);
    var key = String(source).toLowerCase().trim();
    var map = {
      'instagram': 'instagram',
      'ig': 'instagram',
      'youtube': 'youtube',
      'yt': 'youtube',
      'facebook': 'facebook',
      'fb': 'facebook',
      'tiktok': 'tiktok',
      'tt': 'tiktok',
      'linkedin': 'linkedin',
      'in': 'linkedin',
      'reddit': 'reddit',
      'r': 'reddit',
      'bsky': 'bsky',
      'bluesky': 'bsky',
      'news': 'news',
      'newspaper': 'news',
      'site': 'site',
      'website': 'site',
      'blog': 'site'
    };
    return _brandLogoSVG(map[key] || 'default', size);
  }

  var AVATAR_PALETTE = [
    { bg: '#e0e7ff', fg: '#3730a3' },
    { bg: '#fee2e2', fg: '#991b1b' },
    { bg: '#dcfce7', fg: '#166534' },
    { bg: '#fef3c7', fg: '#92400e' },
    { bg: '#cffafe', fg: '#155e75' },
    { bg: '#fae8ff', fg: '#86198f' },
    { bg: '#ffe4e6', fg: '#9f1239' },
    { bg: '#dbeafe', fg: '#1e3a8a' },
    { bg: '#fed7aa', fg: '#7c2d12' },
    { bg: '#d1fae5', fg: '#065f46' },
    { bg: '#fce7f3', fg: '#831843' },
    { bg: '#ede9fe', fg: '#4c1d95' }
  ];

  function _hashString(str) {
    var s = String(str || '');
    var h = 2166136261 >>> 0;
    for (var i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function _domainFromUrl(url) {
    try {
      var s = String(url || '').replace(/^https?:\/\//i, '');
      s = s.split('/')[0];
      s = s.replace(/^www\./i, '').split(':')[0];
      return s || '';
    } catch (e) { return ''; }
  }

  function authorInitials(mentionOrName) {
    var name = '';
    if (typeof mentionOrName === 'string') {
      name = mentionOrName;
    } else if (mentionOrName && typeof mentionOrName === 'object') {
      name = String(mentionOrName.author_name || mentionOrName.author_username || '').trim();
      if (!name) {
        var d = _domainFromUrl(mentionOrName.url);
        if (d) name = d.split('.')[0];
      }
    }
    name = String(name || '').trim();
    if (!name) return '??';
    name = name.replace(/^@+/, '');
    var parts = name.split(/[\s_\-+.\/]/).filter(function (p) { return p; });
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    var first = name[0] || '';
    var second = name.length >= 2 ? name[1] : '';
    return (first + second).toUpperCase();
  }

  function avatarPalette(mentionOrName) {
    var key = typeof mentionOrName === 'string'
      ? mentionOrName
      : String(mentionOrName.author_name || mentionOrName.author_username || mentionOrName.url || Math.random());
    var pal = AVATAR_PALETTE[_hashString(key) % AVATAR_PALETTE.length];
    return { bg: pal.bg, fg: pal.fg };
  }

  function renderAuthorAvatar(mention, sizeClass) {
    sizeClass = sizeClass || 'avatar-md';
    var initials = authorInitials(mention);
    var pal = avatarPalette(mention);
    return '<div class="avatar ' + sizeClass + '" style="background-color:' + pal.bg + ';color:' + pal.fg + ';">' + escapeHtml(initials) + '</div>';
  }

  function formatNumber(n, compact) {
    n = Number(n) || 0;
    if (compact) {
      if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
      if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
      if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
      return String(n);
    }
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function formatPercent(p) {
    var num = Number(p) || 0;
    return num.toFixed(1) + '%';
  }

  function formatDateID(iso) {
    if (!iso) return '';
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des'];
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.getDate() + ' ' + months[d.getMonth()];
  }

  function formatDateRangeID(minIso, maxIso) {
    if (!minIso || !maxIso) return '';
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des'];
    var min = new Date(minIso);
    var max = new Date(maxIso);
    if (isNaN(min.getTime()) || isNaN(max.getTime())) return '';
    var minStr = min.getDate() + ' ' + months[min.getMonth()];
    var maxStr = max.getDate() + ' ' + months[max.getMonth()] + ' ' + max.getFullYear();
    if (min.getFullYear() !== max.getFullYear()) {
      minStr += ' ' + min.getFullYear();
    }
    return minStr + ' - ' + maxStr;
  }

  function getInitials(name) {
    if (!name) return '??';
    var clean = String(name).trim().replace(/^[@]/, '');
    if (!clean) return '??';
    var parts = clean.split(/[\s_.-]+/).filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return clean.substring(0, 2).toUpperCase();
  }

  function safeArray(arr) {
    return Array.isArray(arr) ? arr : [];
  }

  function safeObject(obj) {
    return obj && typeof obj === 'object' && !Array.isArray(obj) ? obj : {};
  }

  function showToast(title, message, type, actions) {
    var container = document.getElementById('toastContainer');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'toast ' + (type || '');

    var iconHtml = '';
    if (type === 'error') iconHtml = ICONS.alertCircle;
    else if (type === 'success') iconHtml = ICONS.sparkles;
    else if (type === 'warn') iconHtml = ICONS.alertTriangle;
    else iconHtml = ICONS.activity;

    var actionsHtml = '';
    if (actions && actions.length) {
      actionsHtml = '<div class="toast-actions">';
      actions.forEach(function (a) {
        actionsHtml += '<button class="toast-btn ' + (a.variant || 'primary') + '" data-action="' + (a.id || '') + '">' + (a.label || '') + '</button>';
      });
      actionsHtml += '</div>';
    }

    toast.innerHTML = '<div class="toast-icon">' + iconHtml + '</div><div class="toast-content"><div class="toast-title">' + (title || '') + '</div><div class="toast-message">' + (message || '') + '</div>' + actionsHtml + '</div>';

    if (actions && actions.length) {
      toast.querySelectorAll('.toast-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var act = btn.getAttribute('data-action');
          var actionObj = actions.find(function (a) { return a.id === act; });
          if (actionObj && typeof actionObj.onClick === 'function') {
            actionObj.onClick();
          }
          toast.remove();
        });
      });
    }

    container.appendChild(toast);
    setTimeout(function () {
      if (toast.parentNode) toast.remove();
    }, 8000);
  }

  function clearSkeletons() {
    var containers = [
      { id: 'kpi-row', clearChildren: true },
      { id: 'chart-source', clearChildren: true },
      { id: 'chart-sentiment', clearChildren: true },
      { id: 'chart-hourly', clearChildren: true },
      { id: 'chart-emotion', clearChildren: true },
      { id: 'chart-performance', clearChildren: true },
      { id: 'chart-wordcloud', clearChildren: true },
      { id: 'chart-emojicloud', clearChildren: true },
      { id: 'chart-keyword', clearChildren: true },
      { id: 'table-hashtags', clearChildren: true },
      { id: 'box-engagement', clearChildren: true },
      { id: 'list-authors', clearChildren: true },
      { id: 'demo-gauge', clearChildren: true },
      { id: 'chart-language', clearChildren: true },
      { id: 'chart-country', clearChildren: true },
      { id: 'insight-box', clearChildren: true },
      { id: 'list-negative', clearChildren: true },
      { id: 'mentionsTableBody', clearChildren: true },
      { id: 'list-negative-extra', clearChildren: true },
      { id: 'list-mixed-sample', clearChildren: true }
    ];
    containers.forEach(function (c) {
      var el = document.getElementById(c.id);
      if (el) {
        if (c.id === 'kpi-row') {
          el.innerHTML = '';
        } else if (c.id === 'mentionsTableBody') {
          el.innerHTML = '';
        } else {
          var skel = el.querySelector('.skeleton');
          if (skel) skel.remove();
        }
      }
    });
  }

  var mentionsState = {
    page: 1,
    perPage: 10,
    total: 0,
    filtered: []
  };

  function initTabs() {
    var bar = document.getElementById('tabsBar');
    if (!bar) return;
    var buttons = bar.querySelectorAll('.tab-button');
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var tab = btn.getAttribute('data-tab');
        var allBtns = bar.querySelectorAll('.tab-button');
        allBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        var panels = document.querySelectorAll('.tab-panel');
        panels.forEach(function (p) { p.classList.remove('active'); });
        var activePanel = document.querySelector('.tab-panel[data-panel="' + tab + '"]');
        if (activePanel) activePanel.classList.add('active');
        if (tab === 'mentions' && state.analytics) {
          renderAllMentions(state.analytics);
        }
        if (tab === 'samples' && state.analytics) {
          renderSamples(state.analytics);
        }
      });
    });
  }

  function _shuffle(arr) {
    var a = (arr || []).slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function renderWordCloud(words) {
    var el = document.getElementById('chart-wordcloud');
    var badge = document.getElementById('wordCloudBadge');
    if (!el) return;
    clearSkeletons();
    el = document.getElementById('chart-wordcloud');
    if (!el) return;
    el.innerHTML = '';
    var list = _shuffle(safeArray(words));
    if (badge) badge.textContent = list.length + ' kata';
    if (list.length === 0) {
      el.innerHTML = '<div class="empty-hint">Tidak ada kata yang ditemukan.</div>';
      return;
    }
    var paletteKey = getTheme();
    var palette = WORDCLOUD_PALETTES[paletteKey] || WORDCLOUD_PALETTES.light;
    list.forEach(function (item, i) {
      var w = String(item.word || '');
      var weight = Number(item.weight) || 0;
      var minSize = 13;
      var maxSize = 36;
      var fontSize = Math.round(minSize + (weight / 100) * (maxSize - minSize));
      var opacity = 0.72 + (weight / 100) * 0.28;
      var color = palette[i % palette.length];
      var span = document.createElement('span');
      span.className = 'wc-word';
      span.style.fontSize = fontSize + 'px';
      span.style.color = color;
      span.style.opacity = opacity.toFixed(2);
      span.setAttribute('title', formatNumber(item.count || 0) + ' kali');
      span.textContent = w;
      el.appendChild(span);
    });
  }

  function renderEmojiCloud(emojis) {
    var el = document.getElementById('chart-emojicloud');
    var badge = document.getElementById('emojiCloudBadge');
    if (!el) return;
    el.innerHTML = '';
    var list = _shuffle(safeArray(emojis));
    if (badge) badge.textContent = list.length + ' emoji';
    if (list.length === 0) {
      el.innerHTML = '<div class="empty-hint">Tidak ada emoji yang ditemukan.</div>';
      return;
    }
    list.forEach(function (item) {
      var e = String(item.emoji || '');
      if (!e) return;
      var weight = Number(item.weight) || 0;
      var minSize = 20;
      var maxSize = 44;
      var fontSize = Math.round(minSize + (weight / 100) * (maxSize - minSize));
      var span = document.createElement('span');
      span.className = 'em-item';
      span.style.fontSize = fontSize + 'px';
      span.setAttribute('title', formatNumber(item.count || 0) + ' kali');
      span.textContent = e;
      el.appendChild(span);
    });
  }

  function sentimentBadgeClass(sent) {
    var s = String(sent || '').toLowerCase();
    if (s === 'positive') return 'badge badge-accent';
    if (s === 'negative') return 'badge badge-danger';
    return 'badge badge-warn';
  }

  function sentimentLabel(sent) {
    var s = String(sent || '').toLowerCase();
    if (s === 'positive') return 'Positif';
    if (s === 'negative') return 'Negatif';
    return 'Netral';
  }

  function applyMentionsFilter(allM, searchRaw, sentimentRaw) {
    var search = (searchRaw || '').trim().toLowerCase();
    var sentiment = sentimentRaw || 'all';
    var list = safeArray(allM);
    return list.filter(function (m) {
      if (sentiment !== 'all') {
        if (String(m.sentiment || '').toLowerCase() !== sentiment) return false;
      }
      if (!search) return true;
      var hay = [
        m.text_preview, m.author_name, m.author_username,
        m.keyword, m.source, m.title, m.text, m.emotion
      ].join(' ').toLowerCase();
      return hay.indexOf(search) !== -1;
    });
  }

  function renderAllMentions(analytics) {
    var allM = safeArray(analytics.all_mentions);
    var searchEl = document.getElementById('mentionsSearch');
    var sentEl = document.getElementById('mentionsSentimentFilter');
    var body = document.getElementById('mentionsTableBody');
    var badge = document.getElementById('mentionsBadge');
    var pageText = document.getElementById('mentionsPageText');
    var prevBtn = document.getElementById('mentionsPrev');
    var nextBtn = document.getElementById('mentionsNext');
    var tabBadge = document.getElementById('tabMentionsCount');
    if (tabBadge) tabBadge.textContent = formatNumber(allM.length);
    if (!body) return;

    var searchVal = searchEl ? searchEl.value : '';
    var sentVal = sentEl ? sentEl.value : 'all';
    mentionsState.filtered = applyMentionsFilter(allM, searchVal, sentVal);
    mentionsState.total = mentionsState.filtered.length;

    var totalPages = Math.max(1, Math.ceil(mentionsState.total / mentionsState.perPage));
    if (mentionsState.page > totalPages) mentionsState.page = 1;
    if (mentionsState.page < 1) mentionsState.page = 1;

    if (badge) badge.textContent = formatNumber(mentionsState.total) + ' data';
    if (pageText) pageText.textContent = 'Halaman ' + mentionsState.page + ' dari ' + formatNumber(totalPages);
    if (prevBtn) prevBtn.disabled = mentionsState.page <= 1;
    if (nextBtn) nextBtn.disabled = mentionsState.page >= totalPages;

    body.innerHTML = '';
    if (mentionsState.total === 0) {
      var emptyTr = document.createElement('tr');
      emptyTr.innerHTML = '<td colspan="10" class="empty-row">Tidak ada data yang sesuai filter.</td>';
      body.appendChild(emptyTr);
      return;
    }

    var start = (mentionsState.page - 1) * mentionsState.perPage;
    var end = Math.min(start + mentionsState.perPage, mentionsState.total);
    for (var i = start; i < end; i++) {
      var m = mentionsState.filtered[i];
      var tr = document.createElement('tr');
      var no = i + 1;
      var authorName = String(m.author_name || '').trim();
      var authorUsername = String(m.author_username || '').trim();
      var labelAuthor = authorName || authorUsername || '';
      var url = String(m.url || '').trim();
      var domain = _domainFromUrl(url);
      var shortCode = '';
      if (url && !labelAuthor) {
        var parts = url.replace(/\/$/, '').split('/');
        for (var k = parts.length - 2; k >= 0 && k < parts.length; k++) {
          if (parts[k] && !/^https?:/.test(parts[k]) && parts[k].length > 2 && parts[k].length < 30 && !/\./.test(parts[k])) {
            shortCode = parts[k];
            break;
          }
        }
      }
      if (!labelAuthor) {
        var sourceLabel = String(m.source || '').trim() || domain || 'Post';
        labelAuthor = sourceLabel.charAt(0).toUpperCase() + sourceLabel.slice(1) + ' Post';
      }
      var displayUsername = authorUsername
        ? '@' + authorUsername
        : (shortCode ? shortCode : (domain && authorName !== domain ? domain : ''));
      var avatar = renderAuthorAvatar(m, 'avatar-md');
      var authorCell =
        '<div class="mention-author">' +
          avatar +
          '<div class="ma-stack">' +
            '<span class="ma-name">' + escapeHtml(labelAuthor) + '</span>' +
            (displayUsername ? '<span class="ma-username">' + escapeHtml(displayUsername) + '</span>' : '') +
          '</div>' +
        '</div>';
      var sourcePill = '<span class="mention-source">' + getBrandLogo(m.source, 16) + '<span>' + escapeHtml(String(m.source || 'UNKNOWN').toUpperCase()) + '</span></span>';
      var actionCell = url
        ? '<td><a class="mention-action" href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">Kunjungi ↗</a></td>'
        : '<td class="muted">—</td>';
      tr.innerHTML =
        '<td>' + no + '</td>' +
        '<td>' + sourcePill + '</td>' +
        '<td class="muted">' + formatDateID(String(m.date || '')) + '</td>' +
        '<td>' + authorCell + '</td>' +
        '<td class="muted">' + escapeHtml(String(m.keyword || '-')) + '</td>' +
        '<td class="mention-preview">' + escapeHtml(String(m.text_preview || m.text || m.title || '-')) + '</td>' +
        '<td><span class="' + sentimentBadgeClass(m.sentiment) + '">' + sentimentLabel(m.sentiment) + '</span></td>' +
        '<td class="muted">' + escapeHtml(String(m.emotion || '-')) + '</td>' +
        '<td class="muted">' + formatNumber(m.reach || 0, true) + '</td>' +
        actionCell;
      body.appendChild(tr);
    }
  }

  function bindMentionsControls() {
    var searchEl = document.getElementById('mentionsSearch');
    var sentEl = document.getElementById('mentionsSentimentFilter');
    var prevBtn = document.getElementById('mentionsPrev');
    var nextBtn = document.getElementById('mentionsNext');
    function onChange() {
      mentionsState.page = 1;
      if (state.analytics) renderAllMentions(state.analytics);
    }
    if (searchEl) searchEl.addEventListener('input', debounce(onChange, 180));
    if (sentEl) sentEl.addEventListener('change', onChange);
    if (prevBtn) prevBtn.addEventListener('click', function () {
      if (mentionsState.page > 1) {
        mentionsState.page--;
        if (state.analytics) renderAllMentions(state.analytics);
      }
    });
    if (nextBtn) nextBtn.addEventListener('click', function () {
      var totalPages = Math.max(1, Math.ceil(mentionsState.total / mentionsState.perPage));
      if (mentionsState.page < totalPages) {
        mentionsState.page++;
        if (state.analytics) renderAllMentions(state.analytics);
      }
    });
  }

  function renderSamples(analytics) {
    var allM = safeArray(analytics.all_mentions);
    var negEl = document.getElementById('list-negative-extra');
    var mixEl = document.getElementById('list-mixed-sample');
    if (negEl) {
      negEl.innerHTML = '';
      var negs = allM.filter(function (m) { return String(m.sentiment || '').toLowerCase() === 'negative'; }).slice(0, 20);
      if (negs.length === 0) {
        negEl.innerHTML = '<div class="empty-hint">Tidak ada sampel negatif.</div>';
      } else {
        renderNegativeCardList(negs, negEl, 'danger');
      }
    }
    if (mixEl) {
      mixEl.innerHTML = '';
      var mixed = allM.filter(function (m) {
        var s = String(m.sentiment || '').toLowerCase();
        return s === 'positive' || s === 'neutral';
      }).slice(0, 10);
      if (mixed.length === 0) {
        mixEl.innerHTML = '<div class="empty-hint">Tidak ada sampel positif/netral.</div>';
      } else {
        renderNegativeCardList(mixed, mixEl, 'accent');
      }
    }
  }

  function renderNegativeCardList(list, container, accentClass) {
    safeArray(list).forEach(function (m) {
      var card = document.createElement('div');
      card.className = 'negative-card ' + (accentClass || 'danger');
      var authorName = String(m.author_name || '').trim();
      var authorUsername = String(m.author_username || '').trim();
      var url = String(m.url || '').trim();
      var domain = _domainFromUrl(url);
      var shortCode = '';
      if (url && !(authorName || authorUsername)) {
        var parts = url.replace(/\/$/, '').split('/');
        for (var k = parts.length - 2; k >= 0 && k < parts.length; k++) {
          if (parts[k] && !/^https?:/.test(parts[k]) && parts[k].length > 2 && parts[k].length < 30 && !/\./.test(parts[k])) {
            shortCode = parts[k];
            break;
          }
        }
      }
      var labelAuthor = authorName || authorUsername || '';
      if (!labelAuthor) {
        var sourceLabel = String(m.source || '').trim() || domain || 'Post';
        labelAuthor = sourceLabel.charAt(0).toUpperCase() + sourceLabel.slice(1) + ' Post';
      }
      var srcName = String(m.source || '').toUpperCase();
      var srcBrand = getBrandLogo(m.source, 18);
      var displayUsername = authorUsername
        ? '@' + authorUsername
        : (shortCode ? shortCode : (domain ? domain : ''));
      var header =
        '<div class="nc-head">' +
          '<div class="nc-source">' + srcBrand + '<span>' + escapeHtml(srcName || 'SOURCE') + '</span></div>' +
          '<span class="' + sentimentBadgeClass(m.sentiment) + '">' + sentimentLabel(m.sentiment) + '</span>' +
        '</div>';
      var title = m.title && String(m.title).trim();
      var preview = m.text_preview || m.text || '';
      var full = (title ? title + ' — ' : '') + String(preview || '');
      if (full.length > 320) full = full.slice(0, 320) + '…';
      var visitLink = url
        ? '<a class="nc-visit" href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">Kunjungi ↗</a>'
        : '';
      var avatar = renderAuthorAvatar(m, 'avatar-md');
      var authorStack =
        '<div class="nc-author-stack">' +
          '<div class="nc-author-name">' + escapeHtml(labelAuthor) + '</div>' +
          (displayUsername ? '<div class="nc-author-username">' + escapeHtml(displayUsername) + '</div>' : '') +
        '</div>';
      var meta =
        '<div class="nc-foot">' +
          '<span class="muted">' + escapeHtml(labelAuthor) + '</span>' +
          '<span class="muted">' + formatDateID(String(m.date || '')) + '</span>' +
          visitLink +
        '</div>';
      card.innerHTML = header +
        '<div class="nc-author">' + avatar + authorStack + '</div>' +
        '<p class="nc-text">' + escapeHtml(full) + '</p>' +
        meta;
      container.appendChild(card);
    });
  }

  function debounce(fn, delay) {
    var t;
    return function () {
      var args = arguments;
      var that = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(that, args); }, delay || 200);
    };
  }

  function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"']/g, function (c) {
      if (c === '&') return '&amp;';
      if (c === '<') return '&lt;';
      if (c === '>') return '&gt;';
      if (c === '"') return '&quot;';
      return '&#39;';
    });
  }

  function showEmptyState() {
    var emptyState = document.getElementById('emptyState');
    var content = document.getElementById('dashboardContent');
    if (emptyState) emptyState.classList.remove('hidden');
    if (content) content.classList.add('hidden');
  }

  function hideEmptyState() {
    var emptyState = document.getElementById('emptyState');
    var content = document.getElementById('dashboardContent');
    if (emptyState) emptyState.classList.add('hidden');
    if (content) content.classList.remove('hidden');
  }

  function populateFilterSources(sources) {
    var select = document.getElementById('filterSource');
    if (!select) return;
    var existingOpts = Array.from(select.options).map(function (o) { return o.value; });
    safeArray(sources).forEach(function (s) {
      if (!s || !s.name) return;
      if (existingOpts.indexOf(s.name) === -1) {
        var opt = document.createElement('option');
        opt.value = s.name;
        opt.textContent = s.name.charAt(0).toUpperCase() + s.name.slice(1);
        select.appendChild(opt);
      }
    });
  }

  function getFilteredKPI(analytics, sourceFilter) {
    var overview = safeObject(analytics.overview);
    if (sourceFilter === 'all') {
      return {
        total_mentions: Number(overview.total_mentions) || 0,
        total_reach: Number(overview.total_reach) || 0,
        total_interactions: Number(overview.total_interactions) || 0,
        avg_performance: Number(overview.avg_performance) || 0,
        composite_sentiment: Number(overview.composite_sentiment) || 0,
        peak_hour: Number(overview.peak_hour) || 0
      };
    }
    var sources = safeArray(analytics.source);
    var source = sources.find(function (s) { return s && s.name === sourceFilter; });
    var sourceCount = source ? Number(source.count) || 0 : 0;
    var totalMentionsAll = Number(overview.total_mentions) || 1;
    var ratio = totalMentionsAll > 0 ? sourceCount / totalMentionsAll : 0;
    return {
      total_mentions: sourceCount,
      total_reach: Math.round((Number(overview.total_reach) || 0) * ratio),
      total_interactions: Math.round((Number(overview.total_interactions) || 0) * ratio),
      avg_performance: Number(overview.avg_performance) || 0,
      composite_sentiment: Number(overview.composite_sentiment) || 0,
      peak_hour: Number(overview.peak_hour) || 0
    };
  }

  function renderKPIRow(kpi) {
    var container = document.getElementById('kpi-row');
    if (!container) return;
    container.innerHTML = '';

    var sentimentLabel = kpi.composite_sentiment >= 0.3 ? 'Positif' :
                         kpi.composite_sentiment <= -0.3 ? 'Negatif' : 'Netral';
    var sentimentBadgeClass = kpi.composite_sentiment >= 0.3 ? 'accent' :
                              kpi.composite_sentiment <= -0.3 ? 'danger' : 'neutral';
    var sentimentPct = Math.abs(kpi.composite_sentiment) * 100;

    var cards = [
      {
        color: 'primary',
        icon: ICONS.messageSquare,
        title: 'Total Mentions',
        value: formatNumber(kpi.total_mentions),
        sub: 'Interaksi: ' + formatNumber(kpi.total_interactions),
        badgeClass: 'primary',
        badgeText: formatNumber(kpi.avg_performance) + ' Perf'
      },
      {
        color: 'accent',
        icon: ICONS.radio,
        title: 'Total Reach',
        value: formatNumber(kpi.total_reach, true),
        sub: 'Audience dicapai',
        badgeClass: 'accent',
        badgeText: formatPercent(kpi.total_mentions ? (kpi.total_reach / kpi.total_mentions / 1000) : 0) + ' /Mtn'
      },
      {
        color: kpi.composite_sentiment >= 0.3 ? 'accent' : (kpi.composite_sentiment <= -0.3 ? 'danger' : 'warn'),
        icon: ICONS.smiley,
        title: 'Komposit Sentimen',
        value: kpi.composite_sentiment.toFixed(3),
        sub: 'Skala -1 sampai +1',
        badgeClass: sentimentBadgeClass,
        badgeText: sentimentLabel + ' ' + formatPercent(sentimentPct)
      },
      {
        color: 'warn',
        icon: ICONS.clock,
        title: 'Jam Puncak',
        value: String(kpi.peak_hour).padStart(2, '0') + ':00',
        sub: 'Aktivitas tertinggi',
        badgeClass: 'warn',
        badgeText: 'JAM'
      }
    ];

    cards.forEach(function (c) {
      var col = document.createElement('div');
      col.className = 'col-3';

      var badgeHtml = '';
      if (c.badgeText) {
        badgeHtml = '<span class="kpi-badge ' + c.badgeClass + '">' + c.badgeText + '</span>';
      }

      col.innerHTML = '<div class="kpi-card ' + c.color + '">' +
        '<div class="kpi-header">' +
          '<div class="kpi-title-wrap"><span class="kpi-icon">' + c.icon + '</span><span class="kpi-title">' + c.title + '</span></div>' +
        '</div>' +
        '<div class="kpi-value">' + c.value + '</div>' +
        '<div class="kpi-sub"><span class="kpi-delta">' + c.sub + '</span>' + badgeHtml + '</div>' +
      '</div>';

      container.appendChild(col);
    });
  }

  function renderSourceHBar(sources, sourceFilter) {
    var container = document.getElementById('chart-source');
    if (!container) return;
    container.innerHTML = '';

    var list = safeArray(sources).slice();
    list.sort(function (a, b) { return (Number(b.count) || 0) - (Number(a.count) || 0); });
    var top = list.slice(0, 5);
    var total = top.reduce(function (sum, s) { return sum + (Number(s.count) || 0); }, 0) || 1;

    var wrap = document.createElement('div');
    top.forEach(function (s, i) {
      var count = Number(s.count) || 0;
      var pct = (count / total) * 100;
      var row = document.createElement('div');
      row.className = 'hbar-row';
      row.dataset.source = s.name || '';
      if (sourceFilter !== 'all' && s.name !== sourceFilter) {
        row.style.opacity = '0.35';
      }
      var colorClass = i < 4 ? 'source-color-' + i : 'source-color-default';
      row.innerHTML = '<div class="hbar-label">' + (s.name || '-') + '</div>' +
        '<div class="hbar-bar-outer"><div class="hbar-bar-inner ' + colorClass + '" style="width:' + pct.toFixed(1) + '%"></div></div>' +
        '<div class="hbar-count">' + formatNumber(count) + '<span class="pct">' + formatPercent(pct) + '</span></div>';
      wrap.appendChild(row);
    });

    container.appendChild(wrap);
  }

  function renderSentimentDonut(sentiments, composite) {
    var container = document.getElementById('chart-sentiment');
    if (!container) return;
    container.innerHTML = '';

    var list = safeArray(sentiments);
    var findByName = function (n) {
      var r = list.find(function (s) { return s && s.name === n; });
      return r ? Number(r.count) || 0 : 0;
    };
    var positive = findByName('positive');
    var neutral = findByName('neutral');
    var negative = findByName('negative');
    var total = positive + neutral + negative || 1;

    var colors = { positive: '#10b981', neutral: '#6b7280', negative: '#ef4444' };
    var r = 80;
    var cx = 120;
    var cy = 120;
    var circumference = 2 * Math.PI * r;
    var strokeWidth = 28;
    var posPct = (positive / total) * 100;
    var neuPct = (neutral / total) * 100;
    var negPct = (negative / total) * 100;

    var posLen = (posPct / 100) * circumference;
    var neuLen = (neuPct / 100) * circumference;
    var negLen = (negPct / 100) * circumference;
    var gap = 2;

    var compositeLabel = composite >= 0.3 ? 'Positif' : composite <= -0.3 ? 'Negatif' : 'Netral';
    var compositeColor = composite >= 0.3 ? '#10b981' : composite <= -0.3 ? '#ef4444' : '#6b7280';

    var svg = '<svg viewBox="0 0 240 240" width="240" height="240">' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="#f3f4f6" stroke-width="' + strokeWidth + '"/>' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + colors.positive + '" stroke-width="' + strokeWidth + '" stroke-dasharray="' + posLen + ' ' + (circumference - posLen + gap) + '" stroke-dashoffset="0" stroke-linecap="butt"/>' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + colors.neutral + '" stroke-width="' + strokeWidth + '" stroke-dasharray="' + neuLen + ' ' + (circumference - neuLen + gap) + '" stroke-dashoffset="' + (-posLen - gap) + '" stroke-linecap="butt"/>' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + colors.negative + '" stroke-width="' + strokeWidth + '" stroke-dasharray="' + negLen + ' ' + (circumference - negLen + gap) + '" stroke-dashoffset="' + (-posLen - neuLen - gap * 2) + '" stroke-linecap="butt"/>' +
    '</svg>';

    var legend = '<div class="donut-legend">' +
      '<div class="legend-item"><div class="legend-dot" style="background-color:' + colors.positive + '"></div><div class="legend-info"><div class="legend-name">Positif</div><div class="legend-sub">' + formatNumber(positive) + ' (' + formatPercent(posPct) + ')</div></div></div>' +
      '<div class="legend-item"><div class="legend-dot" style="background-color:' + colors.neutral + '"></div><div class="legend-info"><div class="legend-name">Netral</div><div class="legend-sub">' + formatNumber(neutral) + ' (' + formatPercent(neuPct) + ')</div></div></div>' +
      '<div class="legend-item"><div class="legend-dot" style="background-color:' + colors.negative + '"></div><div class="legend-info"><div class="legend-name">Negatif</div><div class="legend-sub">' + formatNumber(negative) + ' (' + formatPercent(negPct) + ')</div></div></div>' +
    '</div>';

    var center = '<div class="donut-center">' +
      '<div class="donut-center-label">Composite</div>' +
      '<div class="donut-center-value" style="color:' + compositeColor + '">' + (Number(composite) || 0).toFixed(3) + '</div>' +
      '<div class="donut-center-sub">' + compositeLabel + '</div>' +
    '</div>';

    container.innerHTML = '<div class="donut-wrapper"><div class="donut-svg-wrap">' + svg + center + '</div>' + legend + '</div>';
  }

  function renderHourlyVBar(hourly, peakHour) {
    var container = document.getElementById('chart-hourly');
    if (!container) return;
    container.innerHTML = '';

    var hours = new Array(24).fill(0);
    safeArray(hourly).forEach(function (h) {
      var idx = Number(h.hour) || 0;
      if (idx >= 0 && idx < 24) hours[idx] = Number(h.count) || 0;
    });
    var max = Math.max.apply(null, hours) || 1;
    var peak = typeof peakHour === 'number' ? peakHour : hours.indexOf(max);

    var wrap = document.createElement('div');
    wrap.className = 'vbar-wrapper';

    for (var i = 0; i < 24; i++) {
      var col = document.createElement('div');
      col.className = 'vbar-col';
      var count = hours[i];
      var heightPct = (count / max) * 92 + 4;
      var isPeak = i === peak;
      var labelEvery = i % 3 === 0 || isPeak;
      col.innerHTML = '<div class="vbar-item' + (isPeak ? ' peak' : '') + '" style="height:' + heightPct.toFixed(1) + '%"></div>' +
        '<div class="vbar-label">' + (labelEvery ? String(i).padStart(2, '0') : '') + '</div>';
      wrap.appendChild(col);
    }

    container.appendChild(wrap);
  }

  function renderEmotionVBar(emotions) {
    var container = document.getElementById('chart-emotion');
    if (!container) return;
    container.innerHTML = '';

    var list = safeArray(emotions).slice();
    list.sort(function (a, b) { return (Number(b.count) || 0) - (Number(a.count) || 0); });
    var top = list.slice(0, 5);
    if (top.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:#9ca3af;padding:40px 0;">Tidak ada data emosi</div>';
      return;
    }
    var max = top.reduce(function (m, e) { return Math.max(m, Number(e.count) || 0); }, 0) || 1;

    var wrap = document.createElement('div');
    wrap.className = 'emotion-bar-wrapper';

    top.forEach(function (e, i) {
      var count = Number(e.count) || 0;
      var heightPct = (count / max) * 88 + 6;
      var col = document.createElement('div');
      col.className = 'emotion-col';
      col.innerHTML = '<div class="emotion-bar emotion-color-' + i + '" style="height:' + heightPct.toFixed(1) + '%"></div>' +
        '<div class="emotion-count">' + formatNumber(count) + '</div>' +
        '<div class="emotion-name">' + (e.name || '-') + '</div>';
      wrap.appendChild(col);
    });

    container.appendChild(wrap);
  }

  function renderPerformanceHistogram(histogram) {
    var container = document.getElementById('chart-performance');
    if (!container) return;
    container.innerHTML = '';

    var scores = new Array(10).fill(0);
    safeArray(histogram).forEach(function (h) {
      var idx = (Number(h.score) || 1) - 1;
      if (idx >= 0 && idx < 10) scores[idx] = Number(h.count) || 0;
    });
    var max = Math.max.apply(null, scores) || 1;

    var wrap = document.createElement('div');
    wrap.className = 'histogram-wrapper';

    for (var i = 0; i < 10; i++) {
      var count = scores[i];
      var heightPct = (count / max) * 88 + 4;
      var col = document.createElement('div');
      col.className = 'histogram-col';
      col.innerHTML = '<div class="histogram-bar" style="height:' + heightPct.toFixed(1) + '%"></div>' +
        '<div class="histogram-label">' + (i + 1) + '</div>';
      wrap.appendChild(col);
    }

    container.appendChild(wrap);
  }

  function renderKeywordStacked(keywords, crosstab) {
    var container = document.getElementById('chart-keyword');
    if (!container) return;
    container.innerHTML = '';

    var list = safeArray(keywords).slice();
    list.sort(function (a, b) { return (Number(b.count) || 0) - (Number(a.count) || 0); });
    var top = list.slice(0, 3);
    if (top.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:#9ca3af;padding:40px 0;">Tidak ada data keyword</div>';
      return;
    }
    var cross = safeObject(crosstab);

    var wrap = document.createElement('div');

    top.forEach(function (kw) {
      var name = kw.name || '-';
      var total = Number(kw.count) || 0;
      var kwCross = safeObject(cross[name]);
      var pos = Number(kwCross.positive) || 0;
      var neu = Number(kwCross.neutral) || 0;
      var neg = Number(kwCross.negative) || 0;
      var sumFromCross = pos + neu + neg;
      if (sumFromCross === 0 && total > 0) {
        neu = total;
      }
      var rowTotal = pos + neu + neg || 1;
      var posPct = (pos / rowTotal) * 100;
      var neuPct = (neu / rowTotal) * 100;
      var negPct = (neg / rowTotal) * 100;

      var row = document.createElement('div');
      row.className = 'stacked-keyword-row';
      row.innerHTML = '<div class="stacked-keyword-header">' +
        '<span class="stacked-keyword-name">' + name + '</span>' +
        '<span class="stacked-keyword-total">' + formatNumber(total) + ' mentions</span>' +
      '</div>' +
      '<div class="stacked-bar-wrap">' +
        (posPct > 3 ? '<div class="stacked-segment positive" style="flex-basis:' + posPct.toFixed(1) + '%">' + formatPercent(posPct) + '</div>' : '') +
        (neuPct > 3 ? '<div class="stacked-segment neutral" style="flex-basis:' + neuPct.toFixed(1) + '%">' + formatPercent(neuPct) + '</div>' : '') +
        (negPct > 3 ? '<div class="stacked-segment negative" style="flex-basis:' + negPct.toFixed(1) + '%">' + formatPercent(negPct) + '</div>' : '') +
      '</div>';
      wrap.appendChild(row);
    });

    var legend = document.createElement('div');
    legend.className = 'stacked-legend';
    legend.innerHTML = '<div class="legend-item"><div class="legend-dot" style="background-color:#10b981"></div><span>Positif</span></div>' +
      '<div class="legend-item"><div class="legend-dot" style="background-color:#6b7280"></div><span>Netral</span></div>' +
      '<div class="legend-item"><div class="legend-dot" style="background-color:#ef4444"></div><span>Negatif</span></div>';
    wrap.appendChild(legend);

    container.appendChild(wrap);
  }

  function renderHashtagTable(hashtags) {
    var container = document.getElementById('table-hashtags');
    if (!container) return;
    container.innerHTML = '';

    var list = safeArray(hashtags).slice();
    list.sort(function (a, b) { return (Number(b.count) || 0) - (Number(a.count) || 0); });
    var top = list.slice(0, 10);
    if (top.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:#9ca3af;padding:40px 0;">Tidak ada data hashtag</div>';
      return;
    }
    var total = top.reduce(function (s, h) { return s + (Number(h.count) || 0); }, 0) || 1;

    var html = '<div class="hashtag-table-scroll"><table class="hashtag-table"><thead><tr><th>Rank</th><th>Hashtag</th><th style="text-align:right;">Count</th><th style="text-align:right;">Share</th></tr></thead><tbody>';
    top.forEach(function (h, i) {
      var count = Number(h.count) || 0;
      var pct = (count / total) * 100;
      html += '<tr>' +
        '<td style="font-weight:600;color:#9ca3af;width:50px;">#' + (i + 1) + '</td>' +
        '<td><span class="hashtag-name">#' + (h.tag || '-') + '</span></td>' +
        '<td style="text-align:right;"><span class="hashtag-count">' + formatNumber(count) + '</span></td>' +
        '<td style="text-align:right;"><span class="hashtag-pct">' + formatPercent(pct) + '</span></td>' +
      '</tr>';
    });
    html += '</tbody></table></div>';
    container.innerHTML = html;
  }

  function renderEngagementBoxes(engagement) {
    var container = document.getElementById('box-engagement');
    if (!container) return;
    container.innerHTML = '';

    var e = safeObject(engagement);
    var items = [
      { key: 'likes', label: 'Likes', icon: ICONS.thumbUp, cls: 'likes' },
      { key: 'shares', label: 'Shares', icon: ICONS.share, cls: 'shares' },
      { key: 'comments', label: 'Comments', icon: ICONS.messageSquare, cls: 'comments' },
      { key: 'views', label: 'Views', icon: ICONS.eye, cls: 'views' }
    ];

    var wrap = document.createElement('div');
    wrap.className = 'engagement-grid';

    items.forEach(function (it) {
      var val = Number(e[it.key]) || 0;
      var box = document.createElement('div');
      box.className = 'engagement-box';
      box.innerHTML = '<div class="engagement-icon-wrap ' + it.cls + '">' + it.icon + '</div>' +
        '<div class="engagement-info">' +
          '<div class="engagement-label">' + it.label + '</div>' +
          '<div class="engagement-value">' + formatNumber(val, it.key === 'views') + '</div>' +
        '</div>';
      wrap.appendChild(box);
    });

    container.appendChild(wrap);
  }

  function renderTopAuthors(authors) {
    var container = document.getElementById('list-authors');
    if (!container) return;
    container.innerHTML = '';

    var list = safeArray(authors).slice();
    list.sort(function (a, b) {
      var bc = (Number(b.count) || 0) * 1000 + (Number(b.reach) || 0);
      var ac = (Number(a.count) || 0) * 1000 + (Number(a.reach) || 0);
      return bc - ac;
    });
    var top = list.slice(0, 5);
    if (top.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:#9ca3af;padding:40px 0;">Tidak ada data author</div>';
      return;
    }

    var wrap = document.createElement('div');
    wrap.className = 'authors-list';

    top.forEach(function (a) {
      var displayName = a.name || a.username || 'Unknown';
      var username = a.username || '';
      var authorObj = { author_name: displayName, author_username: username, url: '' };
      var avatar = renderAuthorAvatar(authorObj, 'avatar-md');
      var row = document.createElement('div');
      row.className = 'author-row';
      row.innerHTML = avatar +
        '<div class="author-info">' +
          '<div class="author-name">' + escapeHtml(displayName) + '</div>' +
          (username ? '<div class="author-username">' + escapeHtml('@' + username) + '</div>' : '') +
        '</div>' +
        '<div class="author-stats">' +
          '<div class="author-stat"><div class="author-stat-label">Mentions</div><div class="author-stat-value">' + formatNumber(Number(a.count) || 0) + '</div></div>' +
          '<div class="author-stat"><div class="author-stat-label">Reach</div><div class="author-stat-value">' + formatNumber(Number(a.reach) || 0, true) + '</div></div>' +
        '</div>';
      wrap.appendChild(row);
    });

    container.appendChild(wrap);
  }

  function renderDemographicsGauge(demographics) {
    var container = document.getElementById('demo-gauge');
    if (!container) return;
    container.innerHTML = '';

    var d = safeObject(demographics);
    var malePct = Number(d.male_pct);
    var femalePct = Number(d.female_pct);
    if (isNaN(malePct) && isNaN(femalePct)) {
      malePct = 50;
      femalePct = 50;
    } else if (isNaN(malePct)) {
      malePct = Math.max(0, 100 - femalePct);
    } else if (isNaN(femalePct)) {
      femalePct = Math.max(0, 100 - malePct);
    }
    var totalPct = malePct + femalePct || 1;
    malePct = (malePct / totalPct) * 100;
    femalePct = (femalePct / totalPct) * 100;

    var r = 70;
    var cx = 100;
    var cy = 100;
    var circumference = 2 * Math.PI * r;
    var strokeWidth = 24;
    var maleLen = (malePct / 100) * circumference;
    var femaleLen = (femalePct / 100) * circumference;
    var gap = 2;

    var svg = '<svg viewBox="0 0 200 200" width="200" height="200">' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="#f3f4f6" stroke-width="' + strokeWidth + '"/>' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="#2563eb" stroke-width="' + strokeWidth + '" stroke-dasharray="' + maleLen + ' ' + (circumference - maleLen + gap) + '" stroke-dashoffset="0"/>' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="#db2777" stroke-width="' + strokeWidth + '" stroke-dasharray="' + femaleLen + ' ' + (circumference - femaleLen + gap) + '" stroke-dashoffset="' + (-maleLen - gap) + '"/>' +
    '</svg>';

    var center = '<div class="gauge-center"><div class="gauge-center-label">Gender</div></div>';

    var legend = '<div class="gauge-legend">' +
      '<div class="legend-item"><div class="legend-dot" style="background-color:#2563eb"></div><div class="legend-info"><div class="legend-name">Laki-laki</div><div class="legend-sub">' + formatPercent(malePct) + '</div></div></div>' +
      '<div class="legend-item"><div class="legend-dot" style="background-color:#db2777"></div><div class="legend-info"><div class="legend-name">Perempuan</div><div class="legend-sub">' + formatPercent(femalePct) + '</div></div></div>' +
    '</div>';

    container.innerHTML = '<div class="gauge-wrapper"><div class="gauge-svg-wrap">' + svg + center + '</div>' + legend + '</div>';
  }

  function renderHBarList(list, maxItems, containerId, colorPrefix) {
    var container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    var arr = safeArray(list).slice();
    arr.sort(function (a, b) { return (Number(b.count) || 0) - (Number(a.count) || 0); });
    var top = arr.slice(0, maxItems);
    if (top.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:#9ca3af;padding:40px 0;">Tidak ada data</div>';
      return;
    }
    var total = top.reduce(function (s, x) { return s + (Number(x.count) || 0); }, 0) || 1;

    var wrap = document.createElement('div');
    top.forEach(function (item, i) {
      var count = Number(item.count) || 0;
      var pct = (count / total) * 100;
      var colorClass = i < 5 ? (colorPrefix || 'source-color') + '-' + i : 'source-color-default';
      var row = document.createElement('div');
      row.className = 'hbar-row';
      row.innerHTML = '<div class="hbar-label">' + (item.name || '-') + '</div>' +
        '<div class="hbar-bar-outer"><div class="hbar-bar-inner ' + colorClass + '" style="width:' + pct.toFixed(1) + '%"></div></div>' +
        '<div class="hbar-count">' + formatNumber(count) + '<span class="pct">' + formatPercent(pct) + '</span></div>';
      wrap.appendChild(row);
    });

    container.appendChild(wrap);
  }

  function renderInsightBox(analytics) {
    var container = document.getElementById('insight-box');
    if (!container) return;
    container.innerHTML = '';

    var overview = safeObject(analytics.overview);
    var metadata = safeObject(analytics.metadata);
    var sources = safeArray(analytics.source).slice();
    sources.sort(function (a, b) { return (Number(b.count) || 0) - (Number(a.count) || 0); });
    var topSource = sources[0];
    var totalMentions = Number(overview.total_mentions) || 0;
    var topSourcePct = topSource && totalMentions > 0 ? ((Number(topSource.count) || 0) / totalMentions) * 100 : 0;
    var composite = Number(overview.composite_sentiment) || 0;
    var sentimentLabel = composite >= 0.3 ? 'positif' : composite <= -0.3 ? 'negatif' : 'netral';
    var peakHour = Number(overview.peak_hour) || 0;
    var avgPerf = Number(overview.avg_performance) || 0;

    var sentences = [];
    sentences.push('Selama periode <strong>' + formatDateRangeID(metadata.min_date, metadata.max_date) + '</strong>, terdapat <strong>' + formatNumber(totalMentions) + ' mentions</strong> dengan komposit sentimen ' + sentimentLabel + ' <strong>' + composite.toFixed(3) + '</strong>.');
    if (peakHour !== null && !isNaN(peakHour)) {
      sentences.push('Puncak aktivitas terjadi di jam <strong>' + String(peakHour).padStart(2, '0') + ':00</strong>.');
    }
    if (topSource) {
      sentences.push('Sumber terbesar adalah <strong>' + topSource.name + '</strong> dengan kontribusi <strong>' + formatPercent(topSourcePct) + '</strong>.');
    }
    if (avgPerf > 0) {
      sentences.push('Rata-rata skor performa konten mencapai <strong>' + avgPerf.toFixed(1) + ' / 10</strong>.');
    }
    var keywords = safeArray(analytics.keyword).slice();
    keywords.sort(function (a, b) { return (Number(b.count) || 0) - (Number(a.count) || 0); });
    if (keywords.length > 0) {
      var topKeywordNames = keywords.slice(0, 3).map(function (k) { return '<strong>' + (k.name || '') + '</strong>'; }).join(', ');
      sentences.push('Keyword yang paling banyak muncul: ' + topKeywordNames + '.');
    }

    var box = document.createElement('div');
    box.className = 'insight-box';
    box.innerHTML = '<p>' + sentences.join(' ') + '</p>';
    container.appendChild(box);
  }

  function renderNegativeSample(samples) {
    var container = document.getElementById('list-negative');
    if (!container) return;
    container.innerHTML = '';

    var list = safeArray(samples).slice(0, 5);
    if (list.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:#9ca3af;padding:32px 0;">Tidak ada sampel konten negatif. Good job!</div>';
      return;
    }

    var wrap = document.createElement('div');
    wrap.className = 'negative-list';

    list.forEach(function (s) {
      var card = document.createElement('div');
      card.className = 'negative-card';
      var title = s.title || s.text || '(Untitled)';
      if (title.length > 120) title = title.substring(0, 120) + '...';
      var text = s.text || '';
      if (text.length > 180) text = text.substring(0, 180) + '...';
      card.innerHTML = '<div class="negative-card-title">' + title + '</div>' +
        '<div class="negative-card-author">' + (s.author || '@unknown') + '</div>' +
        '<div class="negative-card-text">' + text + '</div>';
      wrap.appendChild(card);
    });

    container.appendChild(wrap);
  }

  function updateDateRange(analytics) {
    var el = document.getElementById('dateRange');
    if (!el) return;
    var metadata = safeObject(analytics.metadata);
    var rangeStr = formatDateRangeID(metadata.min_date, metadata.max_date);
    el.innerHTML = ICONS.calendar + '<span>' + (rangeStr || 'Periode tidak tersedia') + '</span>';
  }

  function renderAll(analytics, sourceFilter) {
    sourceFilter = sourceFilter || state.activeSource || 'all';
    var kpi = getFilteredKPI(analytics, sourceFilter);
    renderKPIRow(kpi);
    renderSourceHBar(analytics.source, sourceFilter);
    renderSentimentDonut(analytics.sentiment, analytics.overview ? analytics.overview.composite_sentiment : 0);
    renderHourlyVBar(analytics.hourly, analytics.overview ? analytics.overview.peak_hour : null);
    renderEmotionVBar(analytics.emotion);
    renderPerformanceHistogram(analytics.performance_histogram);
    renderWordCloud(analytics.top_words);
    renderEmojiCloud(analytics.emoji_frequency);
    renderKeywordStacked(analytics.keyword, analytics.sentiment_crosstab_by_keyword);
    renderHashtagTable(analytics.top_hashtags);
    renderEngagementBoxes(analytics.engagement_summary);
    renderTopAuthors(analytics.top_authors);
    renderDemographicsGauge(analytics.demographics);
    renderHBarList(analytics.language, 5, 'chart-language', 'source-color');
    renderHBarList(analytics.country, 5, 'chart-country', 'emotion-color');
    renderInsightBox(analytics);
    renderNegativeSample(analytics.negative_sample);
    updateDateRange(analytics);
    var tabMentionsBadge = document.getElementById('tabMentionsCount');
    var totalM = safeArray(analytics.all_mentions).length;
    if (tabMentionsBadge) tabMentionsBadge.textContent = formatNumber(totalM);
  }

  function onFilterChange(e) {
    var val = e.target.value || 'all';
    state.activeSource = val;
    if (!state.analytics) return;
    var kpi = getFilteredKPI(state.analytics, val);
    renderKPIRow(kpi);
    renderSourceHBar(state.analytics.source, val);
  }

  async function loadDashboard() {
    try {
      var response = await fetch('/api/dashboard/active');
      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }
      var data = await response.json();
      if (!data || data.ok === false) {
        clearSkeletons();
        showEmptyState();
        return;
      }
      state.analytics = data.analytics || {};
      clearSkeletons();
      hideEmptyState();
      populateFilterSources(state.analytics.source);
      renderAll(state.analytics, state.activeSource);
    } catch (err) {
      console.error('Load dashboard error:', err);
      showToast('Gagal memuat dashboard', err.message || 'Terjadi kesalahan saat mengambil data.', 'error', [
        { id: 'retry', label: 'Coba Lagi', variant: 'primary', onClick: loadDashboard }
      ]);
    }
  }

  function initThemeToggle() {
    var btn = document.getElementById('themeToggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var current = getTheme();
      var next = (current === 'dark') ? 'light' : 'dark';
      setTheme(next, true);
    });
    try {
      if (window.matchMedia) {
        var mql = window.matchMedia('(prefers-color-scheme: dark)');
        if (mql.addEventListener) {
          mql.addEventListener('change', function (e) {
            var stored = null;
            try { stored = localStorage.getItem('theme'); } catch (_) {}
            if (stored !== 'light' && stored !== 'dark') {
              setTheme(e.matches ? 'dark' : 'light', false);
            }
          });
        }
      }
    } catch (_) {}
    try {
      window.addEventListener('themechange', function () {
        if (state.analytics) {
          try {
            var a = state.analytics;
            if (a && a.top_words && a.top_words.length) renderWordCloud(a.top_words);
            if (a && a.emoji_frequency && a.emoji_frequency.length) renderEmojiCloud(a.emoji_frequency);
          } catch (_) {}
        }
      });
    } catch (_) {}
  }

  function init() {
    initTabs();
    bindMentionsControls();
    initThemeToggle();
    var select = document.getElementById('filterSource');
    if (select) {
      select.addEventListener('change', onFilterChange);
    }
    loadDashboard();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
