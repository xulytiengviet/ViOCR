(function (root) {
  const core = typeof module === 'object' ? require('./converter') : root.CVNSSConverter;
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ ';
  function unpack(ids) {
    return ids.map(id => {
      if (!Number.isInteger(id) || id < 0 || id > 26) throw Error('Base27 cần số nguyên từ 0 đến 26');
      return alphabet[id];
    }).join('');
  }
  function processLine(raw, mode = 'unicode') {
    const source = raw.normalize('NFC');
    let input = source;
    if (mode === 'base27') {
      const digits = source.replace(/\s/g, '');
      if (!/^(?:\d{2})+$/.test(digits)) throw Error('Mỗi mã Base27 cần đúng hai chữ số 00–26');
      input = unpack(digits.match(/../g).map(Number)).toLowerCase();
    }
    const tokens = (input.match(/\p{L}+| +|[^\p{L} ]+/gu) || []).map(original => {
      const cvss = mode === 'unicode' ? core.fromCqn(original).cvss : original;
      if (!/^[a-z ]+$/i.test(cvss)) return {literal: original, unicode: original};
      const ids = [...cvss.toUpperCase()].map(c => alphabet.indexOf(c));
      const code = [...unpack(ids)].map((c,i) => cvss[i] === cvss[i].toLowerCase() ? c.toLowerCase() : c).join('');
      const canonical = core.fromCvss(code).cqn;
      const preserve = mode === 'unicode' && canonical !== original;
      return {cvss: code, ids, trits: ids.map(id => id.toString(3).padStart(3,'0')), canonical,
        unicode: preserve ? original : canonical, ...preserve && {sourceOverride: original}};
    });
    return {raw, unicode: tokens.map(t => t.unicode).join(''), tokens};
  }
  const api = {processLine, unpack};
  if (typeof module === 'object') module.exports = api;
  else root.ViOCR = api;
})(globalThis);
if (typeof require === 'function' && require.main === module) {
  const lines = JSON.parse(require('node:fs').readFileSync(0,'utf8'));
  process.stdout.write(JSON.stringify(lines.map(s => module.exports.processLine(s, process.argv[2]))));
}
