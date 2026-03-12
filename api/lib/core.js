const crypto = require('crypto');

function json(res, status, data) {
  res.status(status).setHeader('Content-Type', 'application/json; charset=utf-8');
  res.send(JSON.stringify(data));
}

function normalizeText(text = '') {
  return text.toLowerCase().replace(/\s+/g, ' ').replace(/[^\w\u4e00-\u9fff ]/g, '').trim();
}

function dedupeHash(title, content) {
  const base = normalizeText(`${title} ${content}`).slice(0, 600);
  return crypto.createHash('sha256').update(base).digest('hex');
}

function detectLanguage(text) {
  if (/[\u4e00-\u9fff]/.test(text)) return 'zh';
  return 'en';
}

function relevance(text, keywords = []) {
  if (!keywords.length) return false;
  const t = normalizeText(text);
  return keywords.some((k) => t.includes(normalizeText(k)));
}

function sentiment(text, lang) {
  const pos = {
    en: ['good', 'great', 'love', 'success', 'improved'],
    zh: ['好', '支持', '成功', '满意', '提升']
  };
  const neg = {
    en: ['bad', 'risk', 'fail', 'problem', 'complaint', 'angry'],
    zh: ['差', '风险', '失败', '问题', '投诉', '愤怒']
  };
  const t = text.toLowerCase();
  const p = (pos[lang] || pos.en).reduce((acc, w) => acc + (t.match(new RegExp(w, 'g')) || []).length, 0);
  const n = (neg[lang] || neg.en).reduce((acc, w) => acc + (t.match(new RegExp(w, 'g')) || []).length, 0);
  const total = p + n;
  const score = total === 0 ? 0 : (p - n) / total;
  const label = score > 0.2 ? 'positive' : score < -0.2 ? 'negative' : 'neutral';
  return { label, score };
}

async function fetchFeed(url) {
  try {
    const res = await fetch(url, { headers: { 'User-Agent': 'OpinionMonitor/1.0' } });
    const xml = await res.text();
    const items = [];
    const rssMatches = xml.matchAll(/<item>([\s\S]*?)<\/item>/g);
    for (const m of rssMatches) {
      const block = m[1];
      const title = (block.match(/<title><!\[CDATA\[([\s\S]*?)\]\]><\/title>|<title>([\s\S]*?)<\/title>/i) || [,'',''])[1] || (block.match(/<title><!\[CDATA\[([\s\S]*?)\]\]><\/title>|<title>([\s\S]*?)<\/title>/i) || [,'',''])[2] || '';
      const desc = (block.match(/<description><!\[CDATA\[([\s\S]*?)\]\]><\/description>|<description>([\s\S]*?)<\/description>/i) || [,'',''])[1] || (block.match(/<description><!\[CDATA\[([\s\S]*?)\]\]><\/description>|<description>([\s\S]*?)<\/description>/i) || [,'',''])[2] || '';
      const link = (block.match(/<link>([\s\S]*?)<\/link>/i) || [,''])[1] || '';
      items.push({ title: title.trim(), summary: desc.trim(), link: link.trim() });
      if (items.length >= 80) break;
    }
    return items;
  } catch {
    return [];
  }
}

module.exports = {
  json,
  dedupeHash,
  detectLanguage,
  relevance,
  sentiment,
  fetchFeed
};
