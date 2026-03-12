const { json } = require('../../lib/core');
const { listItems } = require('../../lib/store');

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return json(res, 405, { error: 'Method Not Allowed' });
  const id = Number(req.query.id);
  const items = await listItems(id);
  return json(res, 200, items.filter((x) => x.is_alert === 1).slice(0, 200));
};
