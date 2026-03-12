const { listItems, saveItems } = require('./store');
const { dedupeHash, detectLanguage, relevance, sentiment, fetchFeed } = require('./core');

async function runTask(task) {
  const existing = await listItems(task.id);
  const seen = new Set(existing.map((x) => x.dedupe_hash));
  let inserted = 0;

  for (const src of task.sources) {
    const feedItems = await fetchFeed(src);
    for (const entry of feedItems) {
      const text = `${entry.title}\n${entry.summary}`;
      const lower = text.toLowerCase();
      if (!task.keywords.some((k) => lower.includes(String(k).toLowerCase()))) continue;
      if (task.exclude_keywords.some((k) => k && lower.includes(String(k).toLowerCase()))) continue;

      const lang = detectLanguage(text);
      if (task.languages.length && !task.languages.includes(lang)) continue;
      if (!relevance(text, task.keywords)) continue;

      const sent = sentiment(text, lang);
      const h = dedupeHash(entry.title, entry.summary);
      if (seen.has(h)) continue;

      const isAlert = sent.label === 'negative' && Math.abs(sent.score) >= Number(task.alert_threshold || 0.6);
      existing.unshift({
        id: `${task.id}_${h.slice(0, 12)}`,
        task_id: task.id,
        source: src,
        title: entry.title,
        url: entry.link,
        content: entry.summary,
        language: lang,
        relevance: 1,
        sentiment: sent.label,
        sentiment_score: Number(sent.score.toFixed(4)),
        is_alert: isAlert ? 1 : 0,
        dedupe_hash: h,
        created_at: new Date().toISOString()
      });
      seen.add(h);
      inserted += 1;
    }
  }

  await saveItems(task.id, existing.slice(0, 500));
  return inserted;
}

module.exports = { runTask };
