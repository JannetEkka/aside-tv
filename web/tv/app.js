/* Aside for Fire TV. Plain ES2017 so it runs on older Fire OS WebViews; no build step. */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var stage = $('stage');
  var video = $('video');

  // ---------- icons (inline SVG, 24px grid) ----------
  var ICONS = {
    play: '<path d="M7 4.5v15l12-7.5z" fill="currentColor"/>',
    chat: '<path d="M4 5h16v11H9l-5 4z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    user: '<circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7" fill="none" stroke="currentColor" stroke-width="2"/>',
    eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" fill="currentColor"/>',
    back: '<path d="M11 6l-7 6 7 6M20 6l-7 6 7 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    book: '<path d="M4 4h6a2 2 0 0 1 2 2v14a2 2 0 0 0-2-2H4zM20 4h-6a2 2 0 0 0-2 2v14a2 2 0 0 1 2-2h6z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    phone: '<rect x="7" y="2" width="10" height="20" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="18" r="1.2" fill="currentColor"/>',
    replay: '<path d="M4 12a8 8 0 1 0 2.3-5.7M4 4v4h4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    restart: '<path d="M6 5v14M19 5l-10 7 10 7z" fill="currentColor"/>'
  };
  function icon(name) { return '<svg class="ico" width="30" height="30" viewBox="0 0 24 24">' + ICONS[name] + '</svg>'; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function ts(sec) { sec = Math.max(0, Math.floor(sec || 0)); var m = Math.floor(sec / 60), s = sec % 60; return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s; }
  function ago(ms) {
    var m = Math.round(ms / 60000);
    if (m < 60) return m + (m === 1 ? ' minute' : ' minutes') + ' ago';
    var h = Math.round(m / 60);
    if (h < 24) return h + (h === 1 ? ' hour' : ' hours') + ' ago';
    var d = Math.round(h / 24);
    return d === 1 ? 'yesterday' : d + ' days ago';
  }

  // ---------- stage scaling ----------
  function fit() {
    var s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    stage.style.transform = 'scale(' + s + ')';
    stage.style.left = ((window.innerWidth - 1920 * s) / 2) + 'px';
    stage.style.top = ((window.innerHeight - 1080 * s) / 2) + 'px';
  }
  window.addEventListener('resize', fit);
  fit();

  // ---------- storage (may be unavailable; the app works without it) ----------
  function load(key, fallback) { try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; } }
  function save(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* private mode */ } }

  var settings = load('aside.settings', { ad: false, voice: true, captions: false });

  // ---------- app state ----------
  var films = [];
  var film = null;          // film being shown or played
  var screen = 'home';
  var horizon = 0;          // furthest point watched: Aside's knowledge ends here
  var lastTick = 0;
  var pausedAt = 0;         // wall clock when playback was paused
  var room = null;          // phone pairing code
  var phoneLive = false;
  var controlsTimer = null;

  // ---------- toast ----------
  var toastTimer;
  function toast(msg, ms) {
    var t = $('toast');
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.add('hidden'); }, ms || 3200);
  }

  // ---------- focus engine: arrows move to the nearest focusable in that direction ----------
  var focused = null;
  function visible(el) { return el.offsetParent !== null || el.getClientRects().length > 0; }
  function focusables(root) { return Array.prototype.filter.call(root.querySelectorAll('[data-focus]'), visible); }
  function setFocus(el) {
    if (focused) focused.classList.remove('focused');
    focused = el || null;
    if (focused) {
      focused.classList.add('focused');
      if (focused._onfocus) focused._onfocus();
    }
  }
  function centre(r) { return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }
  function move(dir) {
    var root = activeLayer();
    if (!root) return false;
    var items = focusables(root);
    if (!items.length) return false;
    if (!focused || items.indexOf(focused) < 0) { setFocus(items[0]); return true; }
    var a = focused.getBoundingClientRect(), ca = centre(a), best = null, bestScore = Infinity;
    items.forEach(function (el) {
      if (el === focused) return;
      var b = el.getBoundingClientRect(), cb = centre(b);
      var dx = cb.x - ca.x, dy = cb.y - ca.y;
      var ok = dir === 'left' ? dx < -4 : dir === 'right' ? dx > 4 : dir === 'up' ? dy < -4 : dy > 4;
      if (!ok) return;
      var along = (dir === 'left' || dir === 'right') ? Math.abs(dx) : Math.abs(dy);
      var across = (dir === 'left' || dir === 'right') ? Math.abs(dy) : Math.abs(dx);
      var score = along + across * 2.5;
      if (score < bestScore) { bestScore = score; best = el; }
    });
    if (best) { setFocus(best); return true; }
    return false;
  }
  function focusFirst(root) { var items = focusables(root); setFocus(items[0] || null); }

  // The top-most open layer receives the keys. In the player with nothing open, keys drive playback.
  function activeLayer() {
    var order = ['welcome', 'pair', 'answer', 'asidebar'];
    for (var i = 0; i < order.length; i++) {
      var el = $(order[i]);
      if (!el.classList.contains('hidden')) return el;
    }
    return screen === 'home' ? $('home') : null;
  }

  function button(label, cls, onEnter, ico) {
    var b = document.createElement('button');
    b.className = cls;
    b.setAttribute('data-focus', '');
    b.innerHTML = (ico ? icon(ico) : '') + '<span>' + esc(label) + '</span>';
    b._enter = onEnter;
    return b;
  }

  // ---------- data ----------
  function api(path, body) {
    var opts = body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {};
    return fetch(path, opts).then(function (r) {
      return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || j.detail || ('HTTP ' + r.status)); return j; });
    });
  }
  function posKey(f) { return 'aside.pos.' + f.id; }
  function savedPos(f) { return load(posKey(f), null); }

  // ---------- HOME ----------
  function renderHome() {
    var cards = $('cards');
    cards.innerHTML = '';
    films.forEach(function (f, i) {
      var c = document.createElement('div');
      c.className = 'card';
      c.setAttribute('data-focus', '');
      c.style.backgroundImage = 'url(' + f.thumb + ')';
      var p = savedPos(f);
      c.innerHTML = '<div class="card-title">' + esc(f.title) + '</div>' +
        (p && p.t > 30 ? '<div class="card-progress" style="width:' + Math.min(100, 100 * p.t / f.duration) + '%"></div>' : '');
      c._onfocus = function () { showHero(f); };
      c._enter = function () { showHero(f); var a = $('hero-actions').querySelector('[data-focus]'); setFocus(a); };
      cards.appendChild(c);
    });
    renderToggles();
    showHero(film || films[0]);
    $('credits').textContent = films.map(function (f) { return f.credit + ' (' + f.license + ')'; }).join('  ·  ');
  }

  function showHero(f) {
    if (!f) return;
    film = f;
    $('home-backdrop').style.backgroundImage = 'url(' + f.backdrop + ')';
    $('hero-meta').textContent = [f.year, f.genre, Math.round(f.duration / 60) + ' min', f.license].join('  ·  ');
    $('hero-title').textContent = f.title;
    $('hero-logline').textContent = f.logline;
    Array.prototype.forEach.call($('cards').children, function (c, i) { c.classList.toggle('current', films[i] === f); });
    var acts = $('hero-actions');
    acts.innerHTML = '';
    var p = savedPos(f);
    if (p && p.t > 30 && p.t < (f.credits_start || f.duration) - 10) {
      acts.appendChild(button('Resume ' + ts(p.t), 'btn primary', function () { play(f, p.t, p.max); }, 'play'));
      acts.appendChild(button('Catch me up first', 'btn', function () { play(f, p.t, p.max, { recap: true }); }, 'book'));
      acts.appendChild(button('Start over', 'btn', function () { play(f, 0, 0); }, 'restart'));
    } else {
      acts.appendChild(button('Play', 'btn primary', function () { play(f, 0, 0); }, 'play'));
    }
  }

  function renderToggles() {
    var box = $('toggles');
    box.innerHTML = '';
    [['ad', 'Audio description'], ['voice', 'Read answers aloud'], ['captions', 'Captions']].forEach(function (d) {
      var t = document.createElement('button');
      t.className = 'toggle' + (settings[d[0]] ? ' on' : '');
      t.setAttribute('data-focus', '');
      t.innerHTML = '<span>' + d[1] + '</span><span class="state">' + (settings[d[0]] ? 'On' : 'Off') + '</span>';
      t._enter = function () {
        settings[d[0]] = !settings[d[0]];
        save('aside.settings', settings);
        t.classList.toggle('on', settings[d[0]]);
        t.querySelector('.state').textContent = settings[d[0]] ? 'On' : 'Off';
      };
      box.appendChild(t);
    });
  }

  // ---------- PLAYER ----------
  function play(f, from, max, opts) {
    film = f;
    screen = 'player';
    $('home').classList.add('hidden');
    $('player').classList.remove('hidden');
    $('ctl-title').textContent = f.title;
    horizon = Math.max(from || 0, max || 0);
    lastTick = from || 0;
    adIndex = 0; adPlaying = null;
    setFocus(null);
    if (video.getAttribute('src') !== f.video) video.src = f.video;
    var start = function () {
      try { video.currentTime = from || 0; } catch (e) { /* not seekable yet */ }
      if (opts && opts.recap) { ask({ mode: 'story', title: 'Catch me up', t: from }); }
      else { video.play().catch(function () { showControls(); }); }
    };
    if (video.readyState >= 1) start(); else video.addEventListener('loadedmetadata', function once() { video.removeEventListener('loadedmetadata', once); start(); });
    showControls();
  }

  function exitPlayer() {
    stopSpeaking();
    stopAd();
    video.pause();
    savePosition();
    closeLayers();
    screen = 'home';
    $('player').classList.add('hidden');
    $('home').classList.remove('hidden');
    renderHome();
    var a = $('hero-actions').querySelector('[data-focus]');
    setFocus(a);
  }

  function savePosition() {
    if (!film || !video.duration) return;
    save(posKey(film), { t: video.currentTime, max: horizon, at: Date.now() });
  }

  function knownUntil() { return Math.max(horizon, video.currentTime || 0); }

  function showControls() {
    $('controls').classList.remove('hidden');
    clearTimeout(controlsTimer);
    if (!video.paused) controlsTimer = setTimeout(function () { $('controls').classList.add('hidden'); }, 3500);
    updateControls();
  }
  function updateControls() {
    var d = video.duration || (film && film.duration) || 1, t = video.currentTime || 0;
    $('progress-fill').style.width = (100 * t / d) + '%';
    $('progress-head').style.left = (100 * t / d) + '%';
    $('ctl-time').textContent = ts(t) + ' / ' + ts(d);
    $('ctl-known').textContent = ts(knownUntil());
  }

  function seek(by) {
    var t = Math.max(0, Math.min((video.duration || 0) - 1, video.currentTime + by));
    video.currentTime = t;
    stopAd();
    showControls();
  }

  function togglePlay() {
    if (video.paused) {
      // Household pattern: back after a long pause? Offer a reminder of where we were.
      if (pausedAt && Date.now() - pausedAt > 5 * 60 * 1000 && video.currentTime > 30) {
        welcome('You paused ' + ago(Date.now() - pausedAt) + '.', 'Want a quick reminder of where we were before you carry on?', 'Remind me', 'Just play');
        return;
      }
      video.play();
    } else {
      video.pause();
    }
    showControls();
  }

  video.addEventListener('pause', function () { pausedAt = Date.now(); if (!activeLayer()) showControls(); savePosition(); pushState(); });
  video.addEventListener('play', function () { pausedAt = 0; if (!activeLayer()) showControls(); pushState(); });
  video.addEventListener('waiting', function () { $('buffering').classList.remove('hidden'); });
  video.addEventListener('playing', function () { failStreak = 0; $('buffering').classList.add('hidden'); });
  video.addEventListener('canplay', function () { $('buffering').classList.add('hidden'); });
  video.addEventListener('seeking', function () { stopAd(); });
  video.addEventListener('error', function () {
    $('buffering').classList.add('hidden');
    if (screen === 'player' && film && failStreak < 3) { failStreak++; reconnect(); return; }
    toast("Couldn't load the film. Check the internet connection.", 6000);
  });

  // The free server sleeps after 15 quiet minutes, and a paused or fully buffered film makes no requests.
  // Keep it awake while someone is on the player; if the film connection drops anyway, wait for the
  // server and carry on from the same second.
  var failStreak = 0, reconnecting = false, onMeta = null;
  setInterval(function () { if (screen === 'player') fetch('/api/health').catch(function () { /* next tick */ }); }, 4 * 60 * 1000);
  function reconnect() {
    if (reconnecting) return;
    reconnecting = true;
    var f = film, t = video.currentTime || lastTick || 0, wasPlaying = !video.paused, tries = 0;
    $('buffering').classList.remove('hidden');
    toast('Connection lost. Reconnecting…', 6000);
    (function attempt() {
      if (screen !== 'player' || film !== f) { reconnecting = false; return; }
      fetch('/api/health').then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); }).then(function () {
        if (onMeta) video.removeEventListener('loadedmetadata', onMeta);
        onMeta = function () {
          video.removeEventListener('loadedmetadata', onMeta); onMeta = null;
          try { video.currentTime = t; } catch (e) { /* not seekable yet */ }
          if (wasPlaying) video.play().catch(function () { showControls(); });
        };
        video.addEventListener('loadedmetadata', onMeta);
        video.src = f.video;
        reconnecting = false;
      }).catch(function () {
        if (++tries > 40) { reconnecting = false; $('buffering').classList.add('hidden'); toast("Couldn't load the film. Check the internet connection.", 6000); return; }
        setTimeout(attempt, 3000);
      });
    })();
  }
  video.addEventListener('ended', function () { savePosition(); });

  // Playback tick: grow the knowledge horizon only by real watching, run AD and captions.
  setInterval(function () {
    if (screen !== 'player') return;
    var t = video.currentTime || 0;
    if (!video.paused && t - lastTick > 0 && t - lastTick < 2.5) horizon = Math.max(horizon, t);
    lastTick = t;
    if (!$('controls').classList.contains('hidden')) updateControls();
    captions(t);
    if (!video.paused) audioDescription(t);
  }, 250);
  setInterval(function () { if (screen === 'player' && !video.paused) { savePosition(); pushState(); } }, 5000);

  // ---------- captions ----------
  function captions(t) {
    var box = $('captions');
    if (!settings.captions || !film || !film.subtitles) { box.classList.add('hidden'); return; }
    var line = null;
    for (var i = 0; i < film.subtitles.length; i++) {
      var s = film.subtitles[i];
      if (s.start <= t && t < s.end) { line = s.text; break; }
    }
    if (line) { box.textContent = line; box.classList.remove('hidden'); } else box.classList.add('hidden');
  }

  // ---------- audio description: narration in the gaps between dialogue ----------
  // While the narrator speaks the film dips a little (not off) and fades back, as broadcast AD does.
  var AD_DUCK = 0.6, AD_VOICE = 1.0;   // clips are loudness-levelled to -16 LUFS
  var adIndex = 0, adPlaying = null, fadeTimer = null;
  function fadeVolume(to, ms) {
    clearInterval(fadeTimer);
    var from = video.volume, steps = Math.max(1, Math.round(ms / 40)), i = 0;
    fadeTimer = setInterval(function () {
      i++;
      video.volume = Math.max(0, Math.min(1, from + (to - from) * i / steps));
      if (i >= steps) clearInterval(fadeTimer);
    }, 40);
  }
  function audioDescription(t) {
    if (!settings.ad || !film || !film.ad || adPlaying) return;
    var cues = film.ad;
    while (adIndex < cues.length && cues[adIndex].start < t - 0.8) adIndex++;
    var c = cues[adIndex];
    if (!c || t < c.start) return;
    adIndex++;
    var a = new Audio(c.audio);
    a.volume = AD_VOICE;
    adPlaying = a;
    fadeVolume(AD_DUCK, 300);
    $('ad-text').textContent = c.text;
    $('ad-caption').classList.remove('hidden');
    var done = function () { if (adPlaying === a) stopAd(); };
    a.addEventListener('ended', done);
    a.addEventListener('error', done);
    a.play().catch(done);
  }
  function stopAd() {
    if (adPlaying) { try { adPlaying.pause(); } catch (e) { /* ignore */ } }
    adPlaying = null;
    fadeVolume(1, 600);
    $('ad-caption').classList.add('hidden');
    if (film && film.ad) {
      var t = video.currentTime || 0;
      adIndex = 0;
      while (adIndex < film.ad.length && film.ad[adIndex].start < t - 0.8) adIndex++;
    }
  }

  // ---------- the Aside bar ----------
  var CHIPS = [
    { label: 'What just happened?', mode: 'now', ico: 'chat' },
    { label: "Who's that?", mode: 'who', ico: 'user' },
    { label: 'Describe the scene', mode: 'describe', ico: 'eye' },
    { label: 'What did I miss?', mode: 'missed', ico: 'back' },
    { label: 'Story so far', mode: 'story', ico: 'book' },
    { label: 'Ask by phone', mode: 'phone', ico: 'phone' }
  ];

  function openBar() {
    video.pause();
    stopAd();
    $('controls').classList.add('hidden');
    $('bar-time').textContent = ts(knownUntil());
    var box = $('chips');
    box.innerHTML = '';
    box.classList.remove('hidden');
    $('missed-chips').classList.add('hidden');
    CHIPS.forEach(function (c) {
      var b = button(c.label, c.mode === 'phone' ? 'chip chip-phone' : 'chip', function () {
        if (c.mode === 'phone') return openPair();
        if (c.mode === 'missed') return openMissed();
        ask({ mode: c.mode, title: c.label });
      }, c.ico);
      box.appendChild(b);
    });
    $('asidebar').classList.remove('hidden');
    focusFirst($('chips'));
  }

  function openMissed() {
    var box = $('missed-chips');
    box.innerHTML = '';
    var now = knownUntil();
    [1, 2, 5, 10].forEach(function (m) {
      if (now < m * 60 - 30) return;
      box.appendChild(button("I've been gone " + m + ' min', 'chip', function () {
        ask({ mode: 'missed', since: Math.max(0, now - m * 60), title: 'What did I miss in the last ' + m + (m === 1 ? ' minute?' : ' minutes?') });
      }, 'back'));
    });
    if (!box.children.length) { ask({ mode: 'story', title: 'Story so far' }); return; }
    $('chips').classList.add('hidden');
    box.classList.remove('hidden');
    focusFirst(box);
  }

  function closeLayers() {
    ['asidebar', 'answer', 'pair', 'welcome'].forEach(function (id) { $(id).classList.add('hidden'); });
    setFocus(null);
  }

  // ---------- asking ----------
  var askSeq = 0, thinkTimer = null;
  function ask(o) {
    var seq = ++askSeq;
    var t = o.t != null ? o.t : knownUntil();
    video.pause();
    stopAd();
    stopSpeaking();
    $('asidebar').classList.add('hidden');
    $('controls').classList.add('hidden');
    var panel = $('answer');
    panel.classList.remove('hidden');
    $('answer-q').textContent = o.title || o.question;
    $('answer-from').classList.toggle('hidden', !o.fromPhone);
    $('answer-body').textContent = '';
    $('answer-moments').innerHTML = '';
    $('answer-guard').innerHTML = '';
    var acts = $('answer-actions');
    acts.innerHTML = '';
    acts.appendChild(button('Back to the film', 'btn', resume, 'play'));
    setFocus(acts.firstChild);
    $('answer-thinking').classList.remove('hidden');
    $('thinking-text').textContent = "Thinking about what we've seen";
    clearTimeout(thinkTimer);
    thinkTimer = setTimeout(function () { $('thinking-text').textContent = 'Checking it against the rest of the film, so nothing slips'; }, 1800);

    api('/api/ask', { film: film.id, t: t, mode: o.mode || 'question', question: o.question || '', since: o.since })
      .then(function (r) {
        if (seq !== askSeq) return;
        showAnswer(r, o);
      })
      .catch(function (e) {
        if (seq !== askSeq) return;
        clearTimeout(thinkTimer);
        $('answer-thinking').classList.add('hidden');
        $('answer-body').textContent = "I couldn't answer just now. The AI service is busy, so give it a moment and try again.";
        var acts = $('answer-actions');
        var retry = button('Try again', 'btn primary', function () { ask(o); }, 'replay');
        acts.insertBefore(retry, acts.firstChild);
        setFocus(retry);
        if (room) api('/api/rooms/' + room + '/answer', { question: o.title || o.question, answer: "Aside couldn't answer just now. Try again in a moment.", t: t }).catch(function () {});
      });
  }

  function showAnswer(r, o) {
    clearTimeout(thinkTimer);
    $('answer-thinking').classList.add('hidden');
    $('answer-body').textContent = r.answer;
    var ms = $('answer-moments');
    ms.innerHTML = '';
    (r.moments || []).forEach(function (sec) {
      ms.appendChild(button('Rewatch ' + ts(sec), 'moment', function () { closeLayers(); video.currentTime = Math.max(0, sec - 2); video.play(); }, 'replay'));
    });
    var g = $('answer-guard');
    if (r.withheld) g.innerHTML = '<span class="rw">Held back:</span> any answer would give away what happens next.';
    else if (r.rewritten) g.innerHTML = '<span class="rw">Rewritten:</span> my first answer gave something away, so I changed it.';
    else if (r.checked) g.innerHTML = '<span class="ok">✓ Spoiler-checked</span> against the rest of the film. I only know up to ' + ts(r.t) + '.';
    var first = ms.querySelector('[data-focus]') || $('answer-actions').querySelector('[data-focus]');
    setFocus(first);
    if (settings.voice) speak(r.answer);
    if (room) api('/api/rooms/' + room + '/answer', { question: o.title || o.question, answer: r.answer, t: r.t }).catch(function () {});
  }

  function resume() {
    stopSpeaking();
    closeLayers();
    video.play();
    showControls();
  }

  // Read aloud with the TV's own speech engine (Android TextToSpeech through the Fire TV wrapper),
  // or the browser's when the app runs outside the wrapper.
  // Fire OS: the TV's own speech engine through the wrapper. Vega's WebView has no speech API, so
  // there the server reads it out (/api/speak). A desktop browser uses its own speech synthesis.
  var voiceAudio = null;
  function speak(text) {
    stopSpeaking();
    if (window.AsideNative && window.AsideNative.speak) { window.AsideNative.speak(text); return; }
    if (window.speechSynthesis && !window.ReactNativeWebView) {
      var u = new SpeechSynthesisUtterance(text);
      u.lang = 'en-US';
      speechSynthesis.speak(u);
      return;
    }
    voiceAudio = new Audio('/api/speak?text=' + encodeURIComponent(text));
    voiceAudio.play().catch(function () { voiceAudio = null; });
  }
  function stopSpeaking() {
    if (voiceAudio) { try { voiceAudio.pause(); } catch (e) { /* ignore */ } voiceAudio = null; }
    if (window.AsideNative && window.AsideNative.stop) window.AsideNative.stop();
    else if (window.speechSynthesis) speechSynthesis.cancel();
  }

  // ---------- welcome back ----------
  function welcome(title, text, yes, no) {
    $('welcome-title').textContent = title;
    $('welcome-text').textContent = text;
    var acts = $('welcome-actions');
    acts.innerHTML = '';
    acts.appendChild(button(yes, 'btn primary', function () { $('welcome').classList.add('hidden'); pausedAt = 0; ask({ mode: 'now', title: 'Where were we?' }); }, 'book'));
    acts.appendChild(button(no, 'btn', function () { $('welcome').classList.add('hidden'); pausedAt = 0; video.play(); }, 'play'));
    $('welcome').classList.remove('hidden');
    focusFirst(acts);
  }

  // ---------- phone pairing ----------
  function openPair() {
    $('asidebar').classList.add('hidden');
    $('pair').classList.remove('hidden');
    setFocus($('pair-done'));
    if (room) return showRoom();
    $('pair-status').textContent = 'Getting a code…';
    api('/api/rooms', {}).then(function (r) {
      room = r.code;
      showRoom();
      pushState();
      poll();
    }).catch(function () { $('pair-status').textContent = "Couldn't reach Aside. Check the connection."; });
  }
  function showRoom() {
    var url = location.origin + '/p/' + room;
    $('pair-qr').src = '/api/qr?data=' + encodeURIComponent(url);
    $('pair-url').textContent = location.host + '/p/' + room;
    $('pair-status').textContent = phoneLive ? 'Phone connected. Ask away.' : 'Waiting for your phone…';
    $('pair-status').classList.toggle('ok', phoneLive);
  }
  $('pair-done')._enter = function () { $('pair').classList.add('hidden'); resume(); };

  function poll() {
    if (!room) return;
    api('/api/rooms/' + room + '/inbox').then(function (r) {
      if (r.phone !== phoneLive) {
        phoneLive = r.phone;
        $('phone-pill').classList.toggle('hidden', !phoneLive);
        if (!$('pair').classList.contains('hidden')) showRoom();
        if (phoneLive) toast('Phone connected. Ask anything out loud.');
      }
      (r.items || []).forEach(function (it) {
        if (screen !== 'player') return;
        $('pair').classList.add('hidden');
        var title = it.mode === 'question' ? '“' + it.text + '”' : (CHIPS.filter(function (c) { return c.mode === it.mode; })[0] || {}).label;
        ask({ mode: it.mode, question: it.text, title: title, fromPhone: true, since: it.mode === 'missed' ? knownUntil() - 120 : undefined });
      });
    }).catch(function () { /* keep polling */ }).then(function () { setTimeout(poll, 1200); });
  }
  function pushState() {
    if (!room || !film) return;
    api('/api/rooms/' + room + '/state', { film: film.id, title: film.title, t: knownUntil(), playing: !video.paused }).catch(function () {});
  }

  // ---------- keys ----------
  function key(name) {
    var layer = activeLayer();
    if (screen === 'player' && !layer) {
      switch (name) {
        case 'enter': case 'playpause': togglePlay(); return true;
        case 'left': seek(-10); return true;
        case 'right': seek(10); return true;
        case 'rewind': seek(-30); return true;
        case 'ff': seek(30); return true;
        case 'up': case 'menu': openBar(); return true;
        case 'down': showControls(); return true;
        case 'back': exitPlayer(); return true;
      }
      return false;
    }
    if (name === 'back') return back();
    if (name === 'enter') { if (focused && focused._enter) focused._enter(); return true; }
    if (name === 'playpause' && screen === 'player') { resume(); return true; }
    if (name === 'menu' && screen === 'player' && layer === $('asidebar')) { closeLayers(); return true; }
    if (name === 'up' || name === 'down' || name === 'left' || name === 'right') {
      var moved = move(name);
      if (!moved && name === 'down' && layer === $('asidebar')) { closeLayers(); video.play(); }
      return true;
    }
    return false;
  }

  // Back closes the top layer; returns false on the home screen so the app can exit.
  function back() {
    var layer = activeLayer();
    if (screen === 'player') {
      if (layer === $('asidebar') && !$('missed-chips').classList.contains('hidden')) { openBar(); return true; }
      if (layer) { stopSpeaking(); closeLayers(); if (layer !== $('welcome')) video.play(); else video.play(); return true; }
      exitPlayer();
      return true;
    }
    return false;
  }

  var KEYMAP = {
    ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right', Enter: 'enter', ' ': 'playpause',
    Escape: 'back', Backspace: 'back', GoBack: 'back', BrowserBack: 'back',
    MediaPlayPause: 'playpause', MediaPlay: 'playpause', MediaPause: 'playpause',
    MediaRewind: 'rewind', MediaFastForward: 'ff', ContextMenu: 'menu', m: 'menu', ',': 'rewind', '.': 'ff'
  };
  var CODEMAP = { 37: 'left', 38: 'up', 39: 'right', 40: 'down', 13: 'enter', 27: 'back', 8: 'back', 179: 'playpause', 227: 'rewind', 228: 'ff', 93: 'menu' };
  document.addEventListener('keydown', function (e) {
    var name = KEYMAP[e.key] || CODEMAP[e.keyCode];
    if (name && key(name)) e.preventDefault();
    else if (name === 'back' && window.ReactNativeWebView) {
      // Vega: Back at the home screen leaves the app (the shell exits on this message).
      window.ReactNativeWebView.postMessage('EXIT_APP');
      e.preventDefault();
    }
  });

  // The Fire TV wrapper sends Back, Menu and media keys here (see tv-app/).
  window.asideKey = function (name) { return key(name); };
  window.asideBack = function () { return back(); };

  // ---------- start ----------
  api('/api/films').then(function (list) {
    films = list;
    if (!films.length) throw new Error('no films');
    renderHome();
    var a = $('hero-actions').querySelector('[data-focus]');
    setFocus(a);
  }).catch(function () {
    $('hero-title').textContent = 'Aside';
    $('hero-logline').textContent = "Couldn't reach the Aside service. Check the internet connection and open the app again.";
  });
})();
