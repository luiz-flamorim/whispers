// ── Configuration ─────────────────────────────────────────────────────────────
// Path to the logs folder, relative to this file.
const LOGS_PATH = '../logs/';

// Add new log filenames here after each chain run.
const LOG_FILES = [
    'chain_20260415_140450.csv',
    'chain_20260415_134320.csv',
    'chain_20260415_133028.csv',
    'chain_20260415_132449.csv',
    'chain_20260414_234414.csv',
];
// ──────────────────────────────────────────────────────────────────────────────


// ── Entry point ───────────────────────────────────────────────────────────────

function init() {
    populateDropdown();
    document.getElementById('log-select').addEventListener('change', onDropdownChange);
}


// ── Dropdown ──────────────────────────────────────────────────────────────────

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
    // Converts "chain_20260415_134320.csv" → "2026-04-15  ·  13:43:20"
    const match = filename.match(/chain_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\.csv/);
    if (!match) return filename;
    return `${match[1]}-${match[2]}-${match[3]}  ·  ${match[4]}:${match[5]}:${match[6]}`;
}

function onDropdownChange(event) {
    const filename = event.target.value;
    if (!filename) return;
    loadLog(filename);
}


// ── Loading ───────────────────────────────────────────────────────────────────

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


// ── CSV parser ────────────────────────────────────────────────────────────────
// Handles quoted fields that contain commas and newlines.

function parseCSV(text) {
    const hops = [];
    let i = 0;

    // skip the header row
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

        // end of row — skip carriage return and/or newline
        if (i < text.length && text[i] === '\r') i++;
        if (i < text.length && text[i] === '\n') i++;
        break;
    }

    return { values: values, nextIndex: i };
}

function parseField(text, startIndex) {
    let i = startIndex;

    if (text[i] === '"') {
        // quoted field — may contain commas and embedded newlines
        let value = '';
        i++; // skip the opening quote

        while (i < text.length) {
            if (text[i] === '"' && i + 1 < text.length && text[i + 1] === '"') {
                // escaped quote ("") → literal "
                value += '"';
                i += 2;
            } else if (text[i] === '"') {
                i++; // skip the closing quote
                break;
            } else {
                value += text[i];
                i++;
            }
        }

        return { value: value, nextIndex: i };
    }

    // unquoted field
    let value = '';
    while (i < text.length && text[i] !== ',' && text[i] !== '\n' && text[i] !== '\r') {
        value += text[i];
        i++;
    }

    return { value: value, nextIndex: i };
}


// ── Rendering ─────────────────────────────────────────────────────────────────

function renderCards(hops) {
    const container = document.getElementById('cards-container');
    container.innerHTML = '';

    if (hops.length === 0) {
        showStateMessage('No hops found in this log.');
        return;
    }

    for (const hop of hops) {
        container.appendChild(createCard(hop));
    }
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


// ── Helpers ───────────────────────────────────────────────────────────────────

function showStateMessage(message) {
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


// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
