const LOGS_PATH = '../logs/';

const LOG_FILES = [
  'chain_20260423_172813.csv',
  'chain_20260423_170952.csv',
  'chain_20260423_161212.csv',
  'chain_20260423_142624.csv',
  'chain_20260420_212230.csv',
  'chain_20260420_204259.csv',
  'chain_20260420_203834.csv',
  'chain_20260420_202255.csv',
  'chain_20260420_180503.csv',
  'chain_20260420_174130.csv',
  'chain_20260420_100742.csv',
  'chain_20260420_095717.csv',
  'chain_20260420_095401.csv',
  'chain_20260419_133948.csv',
  'chain_20260416_161552.csv',
  'chain_20260415_175209.csv',
    'chain_20260415_173227.csv',
    'chain_20260415_140450.csv',
    'chain_20260415_134320.csv',
    'chain_20260415_133028.csv',
    'chain_20260415_132449.csv',
    'chain_20260414_234414.csv',
];

function init() {
    populateDropdown();
    document.getElementById('log-select').addEventListener('change', onDropdownChange);
}

function populateDropdown() {
    const select = document.getElementById('log-select');

    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = '— select a chain log —';
    select.appendChild(placeholder);

    for (const filename of LOG_FILES) {
        const option = document.createElement('option');
        option.value = filename;
        option.textContent = formatLogName(filename);
        select.appendChild(option);
    }
}

function formatLogName(filename) {
    const match = filename.match(/chain_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\.csv/);
    if (!match) return filename;
    return `${match[1]}-${match[2]}-${match[3]}  ·  ${match[4]}:${match[5]}:${match[6]}`;
}

function onDropdownChange(event) {
    const filename = event.target.value;
    if (!filename) return;
    loadLog(filename);
}

function loadLog(filename) {
    showStateMessage('Loading…');

    fetch(LOGS_PATH + filename)
        .then(function (response) {
            if (!response.ok) throw new Error('Could not load ' + filename);
            return response.text();
        })
        .then(function (text) {
            const hops = parseCSV(text);
            renderCards(hops);
        })
        .catch(function (error) {
            showErrorMessage(error.message);
        });
}

function parseCSV(text) {
    const hops = [];
    let i = 0;

    while (i < text.length && text[i] !== '\n') i++;
    i++;

    while (i < text.length) {
        const result = parseRow(text, i);
        i = result.nextIndex;

        if (result.values.length === 5) {
            hops.push({
                time    : result.values[0],
                relay   : result.values[1],
                order   : parseInt(result.values[2], 10),
                received: result.values[3],
                sent    : result.values[4],
            });
        }
    }
    return hops;
}

function parseRow(text, startIndex) {
    const values = [];
    let i = startIndex;

    while (i < text.length) {
        const field = parseField(text, i);
        values.push(field.value);
        i = field.nextIndex;

        if (i < text.length && text[i] === ',') {
            i++;
            continue;
        }

        if (i < text.length && text[i] === '\r') i++;
        if (i < text.length && text[i] === '\n') i++;
        break;
    }

    return { values: values, nextIndex: i };
}

function parseField(text, startIndex) {
    let i = startIndex;

    if (text[i] === '"') {
        let value = '';
        i++;

        while (i < text.length) {
            if (text[i] === '"' && i + 1 < text.length && text[i + 1] === '"') {
                value += '"';
                i += 2;
            } else if (text[i] === '"') {
                i++;
                break;
            } else {
                value += text[i];
                i++;
            }
        }

        return { value: value, nextIndex: i };
    }

    let value = '';
    while (i < text.length && text[i] !== ',' && text[i] !== '\n' && text[i] !== '\r') {
        value += text[i];
        i++;
    }

    return { value: value, nextIndex: i };
}

function renderCards(hops) {
    const container = document.getElementById('cards-container');
    container.innerHTML = '';

    if (hops.length === 0) {
        showStateMessage('No hops found in this log.');
        hideSummary();
        return;
    }

    showSummary(hops);

    for (const hop of hops) {
        container.appendChild(createCard(hop));
    }
}

function showSummary(hops) {
    const summary = document.getElementById('chain-summary');
    const firstHop = hops.find(function (h) { return h.order === 0; });
    const sentence = firstHop ? firstHop.received : '—';
    const hopCount = hops.length;

    summary.textContent =
        'The initial sentence was "' + sentence + '", '
        + 'and the chain ran for ' + hopCount + (hopCount === 1 ? ' hop.' : ' hops.');
    summary.hidden = false;
}

function hideSummary() {
    const summary = document.getElementById('chain-summary');
    summary.hidden = true;
}

function createCard(hop) {
    const hopNumber = String(hop.order).padStart(2, '0');
    const timeOnly  = hop.time.includes(' ') ? hop.time.split(' ')[1] : hop.time;

    const hopEl = document.createElement('span');
    hopEl.className = 'hop-number';
    hopEl.textContent = 'HOP ' + hopNumber;

    const relayEl = document.createElement('span');
    relayEl.className = 'relay-name';
    relayEl.textContent = hop.relay;

    const timeEl = document.createElement('span');
    timeEl.className = 'hop-time';
    timeEl.textContent = timeOnly;

    const header = document.createElement('div');
    header.className = 'card-header';
    header.appendChild(hopEl);
    header.appendChild(relayEl);
    header.appendChild(timeEl);

    const arrow = document.createElement('div');
    arrow.className = 'message-arrow';
    arrow.textContent = '↓';

    const body = document.createElement('div');
    body.className = 'card-body';
    body.appendChild(createMessageBlock('RECEIVED', hop.received));
    body.appendChild(arrow);
    body.appendChild(createMessageBlock('SENT', hop.sent));

    const card = document.createElement('div');
    card.className = 'card';
    card.appendChild(header);
    card.appendChild(body);

    return card;
}

function createMessageBlock(label, text) {
    const labelEl = document.createElement('div');
    labelEl.className = 'message-label';
    labelEl.textContent = label;

    const textEl = document.createElement('div');
    textEl.className = 'message-text';
    textEl.textContent = text;

    const block = document.createElement('div');
    block.className = 'message-block';
    block.appendChild(labelEl);
    block.appendChild(textEl);

    return block;
}

function showStateMessage(message) {
    hideSummary();
    const container = document.getElementById('cards-container');
    container.innerHTML = '';
    const p = document.createElement('p');
    p.className = 'state-message';
    p.textContent = message;
    container.appendChild(p);
}

function showErrorMessage(message) {
    const container = document.getElementById('cards-container');
    container.innerHTML = '';
    const p = document.createElement('p');
    p.className = 'error-message';
    p.textContent = 'Error: ' + message;
    container.appendChild(p);
}

document.addEventListener('DOMContentLoaded', init);