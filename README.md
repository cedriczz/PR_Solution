# 轻量多语言舆情监测工具（Web版）

这是一个给非技术用户的轻量网页工具：
- 你已有关键词即可开始，不需要品牌知识包。
- 系统按频率抓取公开RSS源，匹配关键词并排除无关词。
- 本地模型（轻量规则）做相关性和情绪分类。
- 自动去重后，分为普通结果与告警结果。

## 页面
- Monitoring Config
- Results List
- Alerts List

## 你可以配置的内容
- 任务名称
- 关键词列表
- 排除关键词列表
- 语言列表
- 搜索频率（分钟）
- 告警阈值（0~1）
- 搜索源（RSS URL）

## 快速运行（无需额外依赖）

```bash
python app.py
```

启动后打开：
- `http://127.0.0.1:5000/monitoring`
- `http://127.0.0.1:5000/results`
- `http://127.0.0.1:5000/alerts`

## API（极简）
- `POST /api/tasks`：创建监控任务
- `PUT /api/tasks/<task_id>/keywords`：更新关键词
- `POST /api/tasks/<task_id>/run`：手动触发
- `GET /api/tasks/<task_id>/results`：查询结果
- `GET /api/tasks/<task_id>/alerts`：查询告警

## 示例配置
见 `config_example.json`。

## 架构说明（保持最小化）
- 后端：Python 标准库 HTTP 服务 + SQLite
- 定时器：后台线程轮询执行
- 搜索：RSS抓取 + 关键词匹配
- 去重：内容归一化哈希
- 模型：本地规则模型（相关性/情绪）
- 前端：静态 HTML + 原生 JS

## 轻量部署建议
单机运行即可；如果需要长期开机运行，可用 `systemd` 托管进程。
