const { json } = require('./lib/core');
const { listTasks, saveTasks, nextTaskId } = require('./lib/store');

module.exports = async function handler(req, res) {
  if (req.method === 'GET') {
    const tasks = await listTasks();
    return json(res, 200, tasks.sort((a, b) => b.id - a.id));
  }

  if (req.method === 'POST') {
    const data = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    const required = ['name', 'keywords', 'exclude_keywords', 'languages', 'frequency_minutes', 'alert_threshold', 'sources'];
    const missing = required.filter((k) => !(k in data));
    if (missing.length) return json(res, 400, { error: `缺少字段: ${missing.join(', ')}` });

    const tasks = await listTasks();
    const id = await nextTaskId();
    tasks.push({
      id,
      name: data.name,
      keywords: data.keywords,
      exclude_keywords: data.exclude_keywords,
      languages: data.languages,
      sources: data.sources,
      frequency_minutes: Number(data.frequency_minutes),
      alert_threshold: Number(data.alert_threshold),
      created_at: new Date().toISOString(),
      last_run: null
    });
    await saveTasks(tasks);
    return json(res, 200, { task_id: id });
  }

  return json(res, 405, { error: 'Method Not Allowed' });
};
