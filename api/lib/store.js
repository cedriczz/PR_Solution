const hasKv = !!(process.env.KV_REST_API_URL && process.env.KV_REST_API_TOKEN);

const mem = {
  counter: 0,
  tasks: [],
  items: {}
};

async function kvCall(path, options = {}) {
  const res = await fetch(`${process.env.KV_REST_API_URL}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${process.env.KV_REST_API_TOKEN}`,
      ...(options.headers || {})
    }
  });
  if (!res.ok) throw new Error(`KV 调用失败: ${res.status}`);
  return res.json();
}

async function kvGetJson(key, fallback) {
  const data = await kvCall(`/get/${encodeURIComponent(key)}`);
  if (!data.result) return fallback;
  try {
    return JSON.parse(data.result);
  } catch {
    return fallback;
  }
}

async function kvSetJson(key, value) {
  return kvCall(`/set/${encodeURIComponent(key)}/${encodeURIComponent(JSON.stringify(value))}`, { method: 'POST' });
}

async function nextTaskId() {
  if (!hasKv) {
    mem.counter += 1;
    return mem.counter;
  }
  const data = await kvCall('/incr/monitor:counter', { method: 'POST' });
  return Number(data.result || 1);
}

async function listTasks() {
  if (!hasKv) return mem.tasks;
  return kvGetJson('monitor:tasks', []);
}

async function saveTasks(tasks) {
  if (!hasKv) {
    mem.tasks = tasks;
    return;
  }
  await kvSetJson('monitor:tasks', tasks);
}

async function listItems(taskId) {
  if (!hasKv) return mem.items[taskId] || [];
  return kvGetJson(`monitor:items:${taskId}`, []);
}

async function saveItems(taskId, items) {
  if (!hasKv) {
    mem.items[taskId] = items;
    return;
  }
  await kvSetJson(`monitor:items:${taskId}`, items);
}

module.exports = {
  hasKv,
  nextTaskId,
  listTasks,
  saveTasks,
  listItems,
  saveItems
};
