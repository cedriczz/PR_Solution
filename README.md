# 轻量多语言舆情监测工具（Vercel 可部署版）

你说你是公开网页并且直接部署在 Vercel，这版已按该场景重构：
- 前端：纯静态页面（`monitoring.html / results.html / alerts.html`）
- 后端：Vercel Serverless API（`/api/...`）
- 定时运行：Vercel Cron（`/api/cron/run`）
- 本地模型能力：相关性分类 + 情绪分类（规则模型）

> 保持极简：无品牌知识包、无向量数据库、无多租户、无复杂仪表盘。

---

## 1) 功能满足情况

### 用户配置
- task name
- keyword list
- exclude keyword list
- languages
- search frequency
- alert threshold

### 系统能力
- 定时搜索（Vercel Cron）
- 保存匹配内容（默认内存；推荐接入 Vercel KV 持久化）
- 去重（标题+摘要哈希）
- 本地模型相关性判断
- 本地模型情绪分类
- 结果页展示
- 告警页分离展示

---

## 2) 页面
- `/monitoring.html` Monitoring Config
- `/results.html` Results List
- `/alerts.html` Alerts List

---

## 3) API
- `POST /api/tasks` 创建监控任务
- `PUT /api/tasks/{id}/keywords` 更新关键词
- `POST /api/tasks/{id}/run` 手动触发
- `GET /api/tasks/{id}/results` 查询结果
- `GET /api/tasks/{id}/alerts` 查询告警
- `GET /api/cron/run` 定时器调用入口

---

## 4) 在 Vercel 部署

1. 将仓库导入 Vercel。
2. Framework Preset 选 `Other`。
3. 保持默认构建（本项目无需构建步骤）。
4. 部署后直接访问页面。

### 可选：开启持久化（推荐）
默认不配置 KV 时，数据保存在函数内存（适合演示）。
生产建议配置：
- `KV_REST_API_URL`
- `KV_REST_API_TOKEN`

配置后任务与结果将持久化保存。

---

## 5) 本地运行（可选）

```bash
npx vercel dev
```

打开：
- `http://localhost:3000/monitoring.html`

---

## 6) 示例配置
请参考 `config_example.json`。
