const { json } = require('../../lib/core');
const { listTasks, saveTasks } = require('../../lib/store');
const { runTask } = require('../../lib/run-task');

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return json(res, 405, { error: 'Method Not Allowed' });
  const id = Number(req.query.id);
  const tasks = await listTasks();
  const task = tasks.find((t) => t.id === id);
  if (!task) return json(res, 404, { error: '任务不存在' });

  const inserted = await runTask(task);
  task.last_run = new Date().toISOString();
  await saveTasks(tasks);
  return json(res, 200, { inserted });
};
