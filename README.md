# Thatched Study · 茅屋夜话

把清代纪昀的《阅微草堂笔记》翻译成英文，配西方读者看得懂的文化注释，做一个面向海外灵性 / 东方哲学 / 短篇志怪受众的英文博客 + Kindle 电子书矩阵。

---

## 项目定位

- **内容源**：《阅微草堂笔记》（清·纪昀，公版无版权风险）
- **目标受众**：海外对中国志怪、佛道因果、清代社会感兴趣的英文读者
- **变现路径**：
  1. 自建博客 → Google AdSense 广告收入（主收入）
  2. 攒够 30+ 篇 → 打包 Kindle 电子书（KDP 70% 版税，靠注释/导读破解公版 35% 限制）
  3. 同步 Medium / Substack 截流引流（不放主仓库）

## 技术栈

- **生成**：Node.js + marked + gray-matter，纯静态 HTML 输出
- **托管**：Cloudflare Pages（免费 + 全球 CDN + 自动 HTTPS）
- **域名**：Cloudflare Registrar（原价 $9.77/年）
- **分析**：Google Analytics 4 + Google Search Console
- **广告**：Google AdSense

不用 Hugo / Astro 等框架，方便主人后续自己改。

## 目录结构

```
yuewei-translation/
├── posts/              # Markdown 翻译稿（带 frontmatter）
├── templates/          # HTML 模板（post.html / index.html）
├── assets/             # CSS / 静态资源
├── scripts/build.js    # 构建脚本
├── dist/               # 构建产物（git 忽略）
├── package.json
└── README.md
```

## 本地构建

```bash
cd yuewei-translation
npm install              # 装 marked + gray-matter
node scripts/build.js    # 生成 dist/
```

打开 `dist/index.html` 预览即可。

## 写作规范

- 一篇 = 一个 Markdown 文件，放在 `posts/`，文件名 `NNN-slug.md`
- 必填 frontmatter：`title / slug / date / chinese_title / source / category / tags / excerpt`
- 正文先英文翻译，再原文 `<details>` 折叠，最后译者随笔（Translator's Note）
- 文化典故用 marked footnote 语法 `[^1]`，每则 5-10 个注释起步
- 风格定调：**保留中国意象不硬翻西方对应词**，关键术语保留拼音 + 脚注解释

## 待主人决策（部署前必须定）

- [ ] **域名**：旺财候选清单
  - `thatchedstudy.com`（最推荐，紧扣"阅微草堂"意境，SEO 友好）
  - `yueweitales.com`（音译，品牌识别度高）
  - `jixiaolan.com`（作者名）
  - `thatchedhut.com`
  - `studyofstrange.com`
  - `qingtales.com`
- [ ] **Cloudflare + GitHub 账号**：用现有的，还是新注册海外身份？
- [ ] **AdSense 账号**：用主人已有的，还是新申请绑这个域名？
- [ ] **首篇翻译质量**：是否合格，风格是否需要调整？

## 下一步流程

1. 主人定域名 → 旺财查可用性
2. 验证 Mac 上外网状态（关键阻塞点）
3. 注册 / 登录 Cloudflare → 买域名
4. 建 GitHub 仓 → 把本目录 push 上去
5. Cloudflare Pages 连仓 → 一键部署
6. 接 AdSense → 审核通过即开始展示广告

---

## 当前进度

- [x] 站点骨架 + 构建脚本跑通
- [x] 首篇《The Pig and the Old Man: A Tale of Karmic Debt》（滦阳消夏录 卷一 第一则）
- [ ] 域名 / 部署
- [ ] 第二篇《The Fox in the Study》（滦阳消夏录 卷一 第二则，沧州刘士玉家狐妖）
