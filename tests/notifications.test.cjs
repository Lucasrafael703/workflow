const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('restaurar a lista pelo cache revalida a leitura; navegação normal não recarrega', () => {
    let reloads = 0;
    const listeners = new Map();
    const window = {
        location: {reload: () => reloads++},
        addEventListener: (name, handler) => listeners.set(name, handler),
    };
    vm.runInNewContext(readFileSync(path.join(__dirname, '../static/js/notifications.js'), 'utf8'), {window});
    listeners.get('pageshow')({persisted: false});
    assert.equal(reloads, 0);
    listeners.get('pageshow')({persisted: true});
    assert.equal(reloads, 1);
    listeners.get('pageshow')({persisted: false});
    assert.equal(reloads, 1);
});
