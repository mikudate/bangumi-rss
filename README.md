# Bangumi 收藏 RSS（GitHub Pages）

这个仓库每天 09:00（北京时间）自动抓取 Bangumi 收藏，生成 RSS，发布到 GitHub Pages。你不需要服务器，也不需要懂代码。

**先看效果：** 打开 `preview.html`，里面是真实数据渲染出来的条目样子。

## 第一次上传（只做一次）

本地目录已经提交好了，但还没推到 GitHub。用 GitHub Desktop 最省事：

1. 下载安装 <https://desktop.github.com/download/>
2. 打开 GitHub Desktop，用你的 GitHub 账号登录
3. 菜单 **File → Add local repository**
4. 选择这个目录：
   ```text
   C:\Users\liny\Documents\deepseek-harness\default-workspace\bangumi-rss
   ```
5. 顶部会出现 **Push origin**，点它
6. 打开 <https://github.com/mikudate/bangumi-rss>，确认文件已经出现

如果顶部显示的是 **Publish repository**，点它，取消勾选 **Keep this code private**，名字填 `bangumi-rss`，再点 Publish。

## 你现在只看这 3 步

### 第 1 步：打开 Pages（只设置一次）

1. 打开 <https://github.com/mikudate/bangumi-rss/settings/pages>
2. 找到 **Build and deployment**
3. **Source** 选 **GitHub Actions**

选完不用点保存，页面会自动记住。

### 第 2 步：手动跑一次

1. 打开 <https://github.com/mikudate/bangumi-rss/actions>
2. 左边点 **refresh-bangumi-feeds**
3. 右边点 **Run workflow** → 绿色 **Run workflow**
4. 等 1–2 分钟，看到绿色勾就成功了

### 第 3 步：订阅这两个地址

```text
https://mikudate.github.io/bangumi-rss/bangumi/games.xml
https://mikudate.github.io/bangumi-rss/bangumi/books.xml
```

把地址粘贴到 Feedly / Inoreader / FreshRSS / NetNewsWire 里即可。

---

## 现在里面是示例用户，怎么换成你的

现在 `bangumi-feeds.json` 里是示例用户 `hiyoko91`（游戏）和 `sai`（书籍）。换成你的收藏：

1. 打开 <https://github.com/mikudate/bangumi-rss/blob/main/bangumi-feeds.json>
2. 点右上角铅笔图标 **Edit this file**
3. 找到 `"users": ["hiyoko91"]`，把 `hiyoko91` 换成你的 Bangumi 用户 id
4. 多个用户用英文逗号隔开：

```json
"users": ["user1", "user2", "user3"]
```

5. 拉到页面下面，点 **Commit changes**

提交后 Actions 会自动跑一次；也可以去 Actions 页面手动 **Run workflow**。

### 用户 id 在哪里？

打开你的收藏页，地址栏长这样：

```text
https://bgm.tv/game/list/hiyoko91/collect
                            ^^^^^^^^
                            这个就是用户 id
```

游戏收藏页对应：

```json
"subject_type": "4",
"type": "2"
```

书籍收藏页对应：

```json
"subject_type": "1",
"type": "2"
```

- `type: "2"` = 玩过 / 读过
- `type: "all"` = 想玩、在玩、玩过、搁置、抛弃全部
- `slug` 决定输出文件名：`games` → `bangumi/games.xml`

---

## 如果打不开 / 没有绿色勾

按顺序检查：

1. **Settings → Pages → Source** 是不是选了 **GitHub Actions**。
2. **Actions** 里点进 `refresh-bangumi-feeds`，看哪一步是红色；红色那一步会写原因。
3. 仓库必须是 **Public**（免费版 Pages 只支持公开仓库）。
4. 第一次跑要等 1–2 分钟，刷新页面再看。
5. 刚提交完配置，Actions 可能需要几秒才出现新的运行记录。

常见错误：

| 现象 | 原因 | 处理 |
|---|---|---|
| `404` | Pages 还没部署，或 Source 没选 Actions | 重跑 Actions，等绿色勾 |
| Actions 红色，提示 `No feeds generated` | 用户 id 写错，或该用户没有公开收藏 | 打开 `https://bgm.tv/user/<id>` 确认 |
| 页面是旧的 | Pages 有缓存 | 等几分钟，或强制刷新 |
| 想立刻刷新 | 每天 09:00 才自动跑 | Actions → Run workflow |

---

## 文件说明（不用全懂）

| 文件 | 作用 | 你要不要改 |
|---|---|---|
| `bangumi-feeds.json` | 用户列表、游戏/书籍、标题 | **只改这个** |
| `tools/bangumi_collections_feed.py` | 抓 API、生成 RSS | 不用改 |
| `feeds/bangumi/*.xml` | 生成出来的 RSS | 不用手改 |
| `feeds/bangumi/bangumi.opml` | 可导入阅读器的 OPML | 不用手改 |
| `.github/workflows/refresh.yml` | 每天自动跑 + 发布 Pages | 不用改 |
| `preview.html` | 效果预览 | 不用管 |
| `rsshub/` | 备选方案：自建 RSSHub | 不用管 |

---

## 想改的地方

### 加更多用户

在对应 feed 的 `users` 数组里继续加：

```json
"users": ["user1", "user2", "user3", "user4"]
```

### 每人一个独立 feed

在 feed 里加 `"split": true`：

```json
{
  "slug": "games",
  "title": "友邻玩过的游戏",
  "users": ["user1", "user2"],
  "subject_type": "4",
  "type": "2",
  "split": true
}
```

会生成 `games-user1.xml`、`games-user2.xml`。

### 改每天跑的时间

打开 `.github/workflows/refresh.yml`，改这一行：

```yaml
- cron: '0 1 * * *'
```

`0 1 * * *` 是 UTC 01:00 = 北京时间 09:00。想改成北京时间 21:00，就是 UTC 13:00：

```yaml
- cron: '0 13 * * *'
```

### 只想要游戏，不要书籍

把 `bangumi-feeds.json` 里 `slug` 为 `books` 的那一整段删掉，注意 JSON 逗号。

---

## 本地预览（可选，不懂可以跳过）

```bash
python tools/bangumi_collections_feed.py \
  --config bangumi-feeds.json \
  --out-dir feeds/bangumi \
  --opml feeds/bangumi/bangumi.opml \
  --base-url http://127.0.0.1:8811

python -m http.server 8811 --directory feeds
```

然后打开：

```text
http://127.0.0.1:8811/bangumi/games.xml
```

---

## 说明

- 只读公开收藏，私密收藏抓不到。
- 数据来自 Bangumi 官方 API，不需要登录。
- 每个用户每次取最新 100 条。
- 修改旧条目的评分/短评会让它排到前面，这和 Bangumi 收藏页的排序一致。
- 仓库是公开的，所以收藏内容也会公开可见。
