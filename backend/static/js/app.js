/* ============================================================
   حالینو — حرکت و تعامل
   هر انیمیشن یکی از این هدف‌ها را دارد: ورود محتوا، تغییر state، بازخورد لمس،
   انتقال بین صفحه‌ها. Progressive enhancement: بدون JS همه‌چیز کار می‌کند.
   prefers-reduced-motion همه‌ی حرکت‌ها را خاموش می‌کند.
   ============================================================ */
(function () {
  'use strict';

  var REDUCE = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var DUR = { short: 150, base: 240, long: 400 };
  var EASE = 'cubic-bezier(.2,.8,.2,1)';

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  // استگر حداکثر روی ۶ عنصر؛ بقیه با هم می‌آیند (فهرست‌های بلند منتظر نمی‌مانند)
  var STAGGER_MAX = 5;
  function stagger(sel) { $$(sel).forEach(function (el, i) { el.style.setProperty('--i', Math.min(i, STAGGER_MAX)); }); }

  /* ---------------------------------------------------- ورود پلکانی */

  ['.main > *', '.cowrd__body > *', '.rec', '.list > .item', '.tile', '.stat', '.rows > li', '.moodchip',
   '.jar__balls .face', '.chart__dot', '.cal__cell.has-mood'].forEach(stagger);

  /* ---------------------------------------------------- شمارنده آمار */

  var FA = '۰۱۲۳۴۵۶۷۸۹';
  function toLatin(s) { return s.replace(/[۰-۹]/g, function (d) { return FA.indexOf(d); }); }
  function toFarsi(n) { return String(n).replace(/\d/g, function (d) { return FA[d]; }); }

  function countUp(el) {
    var m = el.textContent.trim().match(/^([^\d۰-۹]*)([\d۰-۹]+)([^\d۰-۹]*)$/);
    if (!m) return;
    var target = parseInt(toLatin(m[2]), 10);
    if (!target || target > 9999) return;
    var farsi = /[۰-۹]/.test(m[2]);
    var start = null, done = false;
    function render(n) { el.textContent = m[1] + (farsi ? toFarsi(n) : n) + m[3]; }
    function tick(t) {
      if (done) return;
      if (!start) start = t;
      var p = Math.min((t - start) / DUR.long, 1);
      render(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) requestAnimationFrame(tick); else done = true;
    }
    requestAnimationFrame(tick);
    window.setTimeout(function () { if (!done) { done = true; render(target); } }, DUR.long + 100);
  }
  if (!REDUCE) $$('.stat b, .legend__text b').forEach(countUp);

  /* ---------------------------------------------------- رسم نمودار */

  var line = $('.chart__line');
  if (line && !REDUCE && line.getTotalLength) {
    var len = line.getTotalLength();
    line.style.strokeDasharray = len;
    line.style.strokeDashoffset = len;
    void line.getBoundingClientRect();
    line.style.transition = 'stroke-dashoffset ' + DUR.long + 'ms ' + EASE;
    line.style.strokeDashoffset = 0;
  }

  /* ---------------------------------------------------- ریپل (بازخورد لمس) */

  document.addEventListener('pointerdown', function (e) {
    if (REDUCE) return;
    var target = e.target.closest('.btn, .tile, .row, .rec, .fab');
    if (!target) return;
    var r = target.getBoundingClientRect();
    var ripple = document.createElement('span');
    ripple.className = 'ripple';
    var size = Math.max(r.width, r.height) * 1.6;
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - r.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - r.top - size / 2) + 'px';
    target.appendChild(ripple);
    ripple.animate([{ transform: 'scale(0)', opacity: .22 }, { transform: 'scale(1)', opacity: 0 }],
      { duration: DUR.long, easing: EASE, fill: 'forwards' }).onfinish = function () { ripple.remove(); };
  }, { passive: true });

  /* ---------------------------------------------------- کج‌شدن ۳بعدی دایره تاریخ */

  var dial = $('[data-dial]');
  if (dial && !REDUCE) {
    var MAX = 6;
    dial.addEventListener('pointermove', function (e) {
      var r = dial.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - .5;
      var y = (e.clientY - r.top) / r.height - .5;
      dial.style.transform = 'perspective(900px) rotateX(' + (-y * MAX * 2).toFixed(2) + 'deg) rotateY(' + (x * MAX * 2).toFixed(2) + 'deg)';
    });
    ['pointerleave', 'pointerup', 'pointercancel'].forEach(function (ev) {
      dial.addEventListener(ev, function () { dial.style.transform = ''; });
    });
  }

  /* ---------------------------------------------------- نوبار: نشانگر لغزان */

  var tabbar = $('.tabbar');
  if (tabbar) {
    var pill = $('.tabbar__pill', tabbar);
    var tabs = $$('.tab', tabbar);
    function placePill(animate) {
      var active = $('.tab.is-active', tabbar);
      if (!pill || !active) return;
      var bar = tabbar.getBoundingClientRect(), r = active.getBoundingClientRect();
      // فاصله از لبه‌ی inline-start (در RTL = راست)
      var offset = bar.right - r.right;
      if (!animate) pill.style.transition = 'none';
      pill.style.width = r.width + 'px';
      pill.style.transform = 'translateX(' + (-offset) + 'px)';
      if (!animate) { void pill.offsetWidth; pill.style.transition = ''; }
    }
    placePill(false);
    window.addEventListener('resize', function () { placePill(false); });
    // قبل از رفتن به صفحه‌ی بعد، نشانگر همان‌جا می‌لغزد (پیوستگی)
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        tabs.forEach(function (t) { t.classList.remove('is-active'); });
        tab.classList.add('is-active');
        placePill(true);
      });
    });
  }

  /* ---------------------------------------------------- Bottom sheet */

  function openSheet(id) {
    var sheet = document.getElementById(id);
    if (!sheet) return;
    sheet.hidden = false;
    sheet.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(function () { sheet.classList.add('is-open'); });
    document.body.style.overflow = 'hidden';
  }
  function closeSheet(sheet) {
    if (!sheet) return;
    sheet.classList.remove('is-open');
    sheet.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    window.setTimeout(function () { sheet.hidden = true; }, REDUCE ? 0 : DUR.long);
  }
  document.addEventListener('click', function (e) {
    var opener = e.target.closest('[data-open]');
    if (opener) { e.preventDefault(); openSheet(opener.getAttribute('data-open')); return; }
    var closer = e.target.closest('[data-close]');
    if (closer) { e.preventDefault(); closeSheet(closer.closest('.sheet')); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') $$('.sheet.is-open').forEach(closeSheet);
  });

  /* ---------------------------------------------------- انتخاب مود: تأیید فقط با انتخاب */

  $$('form[data-moodform]').forEach(function (form) {
    var submit = $('[data-mood-submit]', form);
    function sync() { if (submit) submit.disabled = !$('input[name=mood]:checked', form); }
    form.addEventListener('change', sync);
    sync();
  });

  /* ---------------------------------------------------- پاپ‌آپ بعد از ثبت مود */

  if (new URLSearchParams(location.search).get('logged') === '1') {
    openSheet('sheet-celebrate');
    // آدرس تمیز می‌ماند تا با رفرش دوباره باز نشود
    if (history.replaceState) history.replaceState(null, '', location.pathname);
  }

  /* ---------------------------------------------------- دو سؤال روز: باز/بسته + skip */

  var qbox = $('[data-qbox]'), qline = $('[data-qline]');
  if (qbox && qline) {
    var KEY = 'halino.q.skip.' + (qbox.getAttribute('data-day') || '');
    var skipped = false;
    try { skipped = sessionStorage.getItem(KEY) === '1'; } catch (err) {}
    function showQ(open) {
      qbox.hidden = !open;
      qline.hidden = open;
      if (open && !REDUCE) qbox.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
    showQ(!skipped && qbox.getAttribute('data-initial') === 'open');
    qline.addEventListener('click', function () { showQ(true); });
    $$('[data-qskip]', qbox).forEach(function (btn) {
      btn.addEventListener('click', function () {
        try { sessionStorage.setItem(KEY, '1'); } catch (err) {}
        showQ(false);
      });
    });
    $$('[data-qanswer]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        closeSheet(btn.closest('.sheet'));
        try { sessionStorage.removeItem(KEY); } catch (err) {}
        showQ(true);
      });
    });
  }

  /* ---------------------------------------------------- صفحه‌ی آیتم: توضیح سه‌خطی + «بیشتر» */

  var desc = $('[data-desc]'), descMore = $('[data-desc-more]');
  if (desc && descMore) {
    descMore.hidden = desc.scrollHeight <= desc.clientHeight + 1;
    descMore.addEventListener('click', function () {
      var open = desc.classList.toggle('is-open');
      descMore.textContent = open ? 'کمتر' : 'بیشتر';
    });
  }

  /* ---------------------------------------------------- صفحه‌ی سؤال روز: پاپ‌آپ یک‌ثانیه‌ای + رد کردن */

  var dq = $('[data-dq]');
  if (dq) {
    $$('.dq__box, .dq__skip, .dq__submit', dq).forEach(function (el, i) { el.style.setProperty('--i', i); });
    var toast = $('[data-dq-toast]');
    function releaseBoxes() { dq.classList.remove('is-waiting'); }
    if (toast) {
      toast.hidden = false;
      if (history.replaceState) history.replaceState(null, '', location.pathname);
      window.setTimeout(function () {
        toast.classList.add('is-gone');
        releaseBoxes();
        window.setTimeout(function () { toast.remove(); }, REDUCE ? 0 : DUR.long);
      }, 1000);
    } else {
      releaseBoxes();
    }
    // «بعداً جواب می‌دم»: هر دو سؤال رد می‌شوند؛ «امروز» فقط خط ریز پایین را نشان می‌دهد
    $$('[data-qskip-link]', dq).forEach(function (link) {
      link.addEventListener('click', function () {
        try { sessionStorage.setItem('halino.q.skip.' + (dq.getAttribute('data-day') || ''), '1'); } catch (err) {}
      });
    });
  }

  /* ---------------------------------------------------- پیام‌ها می‌روند */

  $$('.msg').forEach(function (msg, i) {
    window.setTimeout(function () {
      msg.classList.add('is-gone');
      window.setTimeout(function () { msg.remove(); }, DUR.base);
    }, 3000 + i * 300);
  });

  /* ---------------------------------------------------- details نرم */

  $$('details').forEach(function (details) {
    var summary = $('summary', details);
    var body = summary && summary.nextElementSibling;
    if (!summary || !body || REDUCE) return;
    summary.addEventListener('click', function (e) {
      if (details.open) {
        e.preventDefault();
        body.style.overflow = 'hidden';
        body.animate([{ height: body.offsetHeight + 'px', opacity: 1 }, { height: '0px', opacity: 0 }],
          { duration: DUR.base, easing: EASE }).onfinish = function () { details.open = false; body.style.overflow = ''; };
      } else {
        requestAnimationFrame(function () {
          var h = body.offsetHeight;
          body.style.overflow = 'hidden';
          body.animate([{ height: '0px', opacity: 0 }, { height: h + 'px', opacity: 1 }],
            { duration: DUR.base, easing: EASE }).onfinish = function () { body.style.overflow = ''; };
        });
      }
    });
  });

  /* ---------------------------------------------------- ویزارد آنبوردینگ */

  var wizard = $('[data-wizard]');
  if (wizard) {
    var steps = $$('[data-step]', wizard);
    var bar = $('[data-progress]', wizard), counter = $('[data-counter]', wizard);
    var prevBtn = $('[data-prev]', wizard), nextBtn = $('[data-next]', wizard), submitBtn = $('[data-submit]', wizard);
    var current = 0, booted = false;
    // هر سؤال اجباری است: یک گزینه، یا «مورد دیگه…» به‌همراه متنش
    function stepValid(step) {
      if (!step.hasAttribute('data-required')) return true;
      var checked = $$('input:checked', step);
      if (!checked.length) return false;
      var other = $('[data-other-input]', step);
      var otherOn = checked.some(function (input) { return input.hasAttribute('data-other'); });
      return !otherOn || !!(other && other.value.trim());
    }
    function sync() {
      var ok = stepValid(steps[current]);
      nextBtn.disabled = !ok;
      submitBtn.disabled = !ok;
    }
    function show(index, dir) {
      steps.forEach(function (step, i) { step.hidden = i !== index; step.classList.remove('from-right', 'from-left'); });
      steps[index].classList.add(dir > 0 ? 'from-right' : 'from-left');
      current = index;
      var last = index === steps.length - 1;
      prevBtn.hidden = index === 0; nextBtn.hidden = last; submitBtn.hidden = !last;
      if (bar) bar.style.width = ((index + 1) / steps.length * 100) + '%';
      if (counter) counter.textContent = toFarsi(index + 1) + ' از ' + toFarsi(steps.length);
      if (booted) wizard.scrollIntoView({ block: 'start', behavior: REDUCE ? 'auto' : 'smooth' });
      booted = true;
      sync();
    }
    prevBtn.addEventListener('click', function () { show(Math.max(current - 1, 0), -1); });
    nextBtn.addEventListener('click', function () { if (stepValid(steps[current])) show(Math.min(current + 1, steps.length - 1), 1); });
    wizard.addEventListener('input', sync);
    wizard.addEventListener('change', function (e) {
      sync();
      // «مورد دیگه…» منتظر متن می‌ماند
      if (e.target.hasAttribute('data-other') && e.target.checked) {
        var input = $('[data-other-input]', steps[current]);
        if (input) input.focus();
      }
    });
    steps.forEach(function (step, i) {
      $$('input[type=radio]:not([data-other])', step).forEach(function (radio) {
        radio.addEventListener('change', function () {
          if (i < steps.length - 1) window.setTimeout(function () { if (current === i) show(i + 1, 1); }, DUR.base);
        });
      });
    });
    wizard.classList.add('is-ready');
    var start = parseInt(wizard.getAttribute('data-start') || '0', 10);
    show(Math.min(Math.max(start, 0), steps.length - 1), 1);
  }
})();
