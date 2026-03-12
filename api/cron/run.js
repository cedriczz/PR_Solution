const { json } = require('../lib/core');
const { listTasks, saveTasks } = require('../lib/store');
const { runTask } = require('../lib/run-task');

module.exports = async function handler(req, res) {
  const tasks = await listTasks();
  const now = Date.now();
  let touched = 0;

  for (const t of tasks) {
    if (!t.last_run) {
      await runTask(t);
      t.last_run = new Date().toISOString();
      touched += 1;
      continue;
    }
    const diffM = (now - new Date(t.last_run).getTime()) / 60000;
    if (diffM >= Math.max(1, Number(t.frequency_minutes || 30))) {
      await runTask(t);
      t.last_run = new Date().toISOString();
      touched += 1;
    }
  }

  await saveTasks(tasks);
  return json(res, 200, { ok: true, executed_tasks: touched });
};
