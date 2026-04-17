// Parses chain log CSVs into an ordered hop array:
// Rows are sorted by the 'order' column before extraction.

const LOGS_PATH = '../logs/';

const LOG_FILES = [
  'chain_20260416_161552.csv',
  'chain_20260415_175209.csv',
  'chain_20260415_173227.csv',
  'chain_20260415_140450.csv',
  'chain_20260415_134320.csv',
  'chain_20260415_133028.csv',
  'chain_20260415_132449.csv',
  'chain_20260414_234414.csv',
];

// Fetches a log file and returns the hop array via callback(err, hops).
function loadHops(filename, callback) {
  fetch(LOGS_PATH + filename)
    .then(function (r) {
      if (!r.ok) throw new Error('Could not load ' + filename);
      return r.text();
    })
    .then(function (text) {
      callback(null, parseCSV(text));
    })
    .catch(function (err) {
      callback(err, []);
    });
}

function parseCSV(text) {
  const rows = [];
  let i = 0;

  // skip header line
  while (i < text.length && text[i] !== '\n') i++;
  i++;

  while (i < text.length) {
    const result = parseRow(text, i);
    i = result.nextIndex;
    if (result.values.length === 5) {
      rows.push({
        order:    parseInt(result.values[2], 10),
        received: result.values[3],
        sent:     result.values[4],
      });
    }
  }

  rows.sort(function (a, b) { return a.order - b.order; });

  // Prepend the original transcript (received by the first relay) then all sent values
  const hopsArray = [];
  if (rows.length > 0) hopsArray.push(rows[0].received);
  for (var r = 0; r < rows.length; r++) hopsArray.push(rows[r].sent);
  return hopsArray;
}

function parseRow(text, startIndex) {
  const values = [];
  let i = startIndex;

  while (i < text.length) {
    const field = parseField(text, i);
    values.push(field.value);
    i = field.nextIndex;

    if (i < text.length && text[i] === ',') { i++; continue; }
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
        value += '"'; i += 2;
      } else if (text[i] === '"') {
        i++; break;
      } else {
        value += text[i++];
      }
    }
    return { value: value, nextIndex: i };
  }

  let value = '';
  while (i < text.length && text[i] !== ',' && text[i] !== '\n' && text[i] !== '\r') {
    value += text[i++];
  }
  return { value: value, nextIndex: i };
}
