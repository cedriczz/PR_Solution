const { json } = require('../../lib/core');
const { listTasks, saveTasks } = require('../../lib/store');

module.exports = async function handler(req, res) {
  if (req.method !== 'PUT') return json(res, 405, { error: 'Method Not Allowed' });
  const id = Number(req.query.id);
  const data = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
  if (!Array.isArray(data.keywords) || !Array.isArray(data.exclude_keywords)) {
    return json(res, 400, { error: '需要 keywords 和 exclude_keywords' });
  }

  const tasks = await listTasks();
  const idx = tasks.findIndex((t) => t.id === id);
  if (idx === -1) return json(res, 404, { error: '任务不存在' });

  tasks[idx].keywords = data.keywords;
  tasks[idx].exclude_keywords = data.exclude_keywords;
  await saveTasks(tasks);
  return json(res, 200, { ok: true });
};
