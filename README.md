# Footwear Tech — 运动鞋科技资讯 · 论文 · 专利

每日自动更新的静态站（苹果官网风格：白底、留白、大标题、半透明导航）。
检索维度严格按三份来源清单执行：`footwear-tech-feeds.md`（资讯）、
`footwear-papers-sources.md`（论文）、`footwear-patent-sources.md`（专利）。

## 上线（GitHub Pages，免费）

1. 在 GitHub 新建一个仓库（如 `footwear-tech`），把本目录全部文件推上去。
2. 仓库 **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。
3. 到 **Actions** 页手动运行一次 “Daily update & deploy”，完成后网址为
   `https://<你的用户名>.github.io/<仓库名>/`，任何人可访问。
4. 之后每天北京时间 08:00 自动抓取并重新部署，无需人工操作。

## 密钥（可选，但强烈建议第一个）

在 **Settings → Secrets and variables → Actions** 添加：

| Secret | 用途 | 获取 |
|---|---|---|
| `OPENALEX_API_KEY` | 论文主力源 OpenAlex；免费 key 有独立额度，无 key 时共享额度常在当天耗尽，脚本会自动退到 PubMed + Crossref | openalex.org 注册免费获取 |
| `LENS_TOKEN` | 专利真实记录（Lens.org） | lens.org 申请 API 访问后创建 Token |
| `EPO_OPS_KEY` / `EPO_OPS_SECRET` | 专利真实记录（EPO OPS） | epo.org/ops 注册 |

未填专利密钥时，专利栏展示的是按「品牌申请人 × CPC 分类」预填的最新公开
检索入口（Espacenet / Google Patents / USPTO / 国家知识产权局），不会伪造记录；
填入后自动替换为真实专利条目。

## 数据与合规说明

- 论文：OpenAlex / PubMed / Crossref / Semantic Scholar 均为清单中的免费学术源；
  知网、Web of Science、Scopus 等需订阅、无公开 API，只作人工补充。
- 专利“最新”指“最新公开”：发明专利一般在申请约 18 个月后公开。
  USPTO 的 PatentsView 已于 2026-03-20 迁入其开放数据门户，原 API 暂停，故不使用旧接口。
  中国专利无公开 API，页面提供国家知识产权局公布公告入口人工核对。
- 资讯：只展示标题、摘要和来源链接；按清单 G 节的保留词/屏蔽词过滤
  （屏蔽 coupon、deal、sale、折扣、优惠等导购内容）。
- 本站只展示元数据与原文链接，不转载全文。

## 本地预览

```bash
python3 scripts/fetch_data.py   # 生成 data/data.json（仅用 Python 标准库）
python3 -m http.server 8000     # 打开 http://localhost:8000
```
