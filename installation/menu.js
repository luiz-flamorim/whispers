// Hidden overlay. Press M to open / close.

(function () {

  var overlay;

  function buildOverlay() {
    overlay = document.createElement('div');
    overlay.id = 'wc-menu';

    overlay.innerHTML = [
      '<div class="wc-inner">',

        '<header class="wc-header">',
          '<h1 class="wc-title">WHISPER CHAIN</h1>',
          '<div class="wc-description">',
            '<p>',
              'Whisper Chain is an <strong>inference experiment</strong> based on ',
              '<a href="https://en.wikipedia.org/wiki/Chinese_whispers" target="_blank" rel="noopener">Chinese Whispers</a> ',
              '(also known as Broken Telephone). In the game, players line up, the first person ',
              'whispers a phrase into the next player\'s ear, and the message travels down the chain ',
              'until the last person reveals what they heard. The result is usually funny, as the ',
              'message often ends up completely different from what started.',
            '</p>',
            '<p>',
              'This project does the same, but with <strong>LLMs</strong> instead of people. ',
              'Each model receives the message and rephrases it in its own words before passing it on ',
              'as a pure <strong>inference</strong> step. The user controls only a few parameters, ',
              'but the number of hops has the biggest impact; fewer hops produce subtle changes, ',
              'while more hops lead to increasingly odd results.',
            '</p>',
          '</div>',
        '</header>',

        '<div class="wc-controls">',
          '<label class="wc-label" for="wc-select">CHAIN LOG</label>',
          '<select id="wc-select" class="wc-select"></select>',
        '</div>',

        '<p class="wc-hint">Press <kbd>M</kbd> to close</p>',

      '</div>',
    ].join('');

    document.body.appendChild(overlay);
  }

  function populateDropdown() {
    var select = document.getElementById('wc-select');

    for (var i = 0; i < LOG_FILES.length; i++) {
      var opt = document.createElement('option');
      opt.value = LOG_FILES[i];
      opt.textContent = formatLogName(LOG_FILES[i]);
      select.appendChild(opt);
    }

    select.value = LOG_FILES[0];

    select.addEventListener('change', function () {
      var filename = this.value;
      if (!filename) return;
      hideMenu();
      loadHops(filename, function (err, hopsArray) {
        if (!err && hopsArray.length) transitionTo(hopsArray);
      });
    });
  }

  function formatLogName(filename) {
    var m = filename.match(/chain_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\.csv/);
    if (!m) return filename;
    return m[1] + '-' + m[2] + '-' + m[3] + '  ·  ' + m[4] + ':' + m[5] + ':' + m[6];
  }

  function showMenu() { overlay.style.display = 'flex'; }
  function hideMenu() { overlay.style.display = 'none'; }

  function init() {
    buildOverlay();
    populateDropdown();
    hideMenu();

    // Auto-load most recent log on startup
    loadHops(LOG_FILES[0], function (err, hopsArray) {
      if (!err && hopsArray.length) transitionTo(hopsArray);
    });

    // M key toggles the menu
    document.addEventListener('keydown', function (e) {
      if (e.key === 'm' || e.key === 'M') {
        overlay.style.display === 'none' ? showMenu() : hideMenu();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', init);

})();
