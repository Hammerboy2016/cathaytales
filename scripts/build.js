#!/usr/bin/env node
/**
 * Cathay Tales — Static Site Generator
 *
 * Usage:
 *   node scripts/build.js
 *
 * Reads:  posts/*.md  (markdown with YAML frontmatter)
 * Writes: dist/index.html, dist/posts/*.html, dist/assets/style.css
 */

const fs = require('fs');
const path = require('path');
const { marked } = require('marked');
const matter = require('gray-matter');

const ROOT = path.resolve(__dirname, '..');
const POSTS_DIR = path.join(ROOT, 'posts');
const TEMPLATES_DIR = path.join(ROOT, 'templates');
const ASSETS_DIR = path.join(ROOT, 'assets');
const STATIC_DIR = path.join(ROOT, 'static');
const DIST_DIR = path.join(ROOT, 'dist');
const DIST_POSTS_DIR = path.join(DIST_DIR, 'posts');
const DIST_HUBS_DIR = path.join(DIST_DIR, 'hubs');
const DIST_ASSETS_DIR = path.join(DIST_DIR, 'assets');

// ---------- marked: enable footnotes via custom extension ----------
// Marked v12+ does not include footnotes by default. We implement a minimal version.
const footnoteRefs = new Map();   // id -> number (per-render)
const footnoteDefs = new Map();   // id -> { number, text }
let footnoteCounter = 0;

function resetFootnotes() {
  footnoteRefs.clear();
  footnoteDefs.clear();
  footnoteCounter = 0;
}

const footnoteExtension = {
  extensions: [
    {
      name: 'footnoteRef',
      level: 'inline',
      start(src) { return src.match(/\[\^/)?.index; },
      tokenizer(src) {
        const rule = /^\[\^([^\]]+)\]/;
        const match = rule.exec(src);
        if (match) {
          return { type: 'footnoteRef', raw: match[0], id: match[1] };
        }
      },
      renderer(token) {
        if (!footnoteRefs.has(token.id)) {
          footnoteCounter++;
          footnoteRefs.set(token.id, footnoteCounter);
        }
        const num = footnoteRefs.get(token.id);
        // tooltip span is filled later in post-process (after defs are collected)
        return `<sup class="footnote-ref" id="fnref-${token.id}"><a href="#fn-${token.id}" data-fn-id="${token.id}">[${num}]</a><span class="footnote-tooltip" data-fn-id="${token.id}"></span></sup>`;
      }
    },
    {
      name: 'footnoteDef',
      level: 'block',
      start(src) { return src.match(/^\[\^/m)?.index; },
      tokenizer(src) {
        const rule = /^\[\^([^\]]+)\]:[ \t]*([^\n]*(?:\n(?![\[\n#])[^\n]*)*)/;
        const match = rule.exec(src);
        if (match) {
          return { type: 'footnoteDef', raw: match[0], id: match[1], text: match[2].trim() };
        }
      },
      renderer(token) {
        // Defer rendering — collect for end-of-document footnote section
        footnoteDefs.set(token.id, { text: token.text });
        return ''; // don't render inline
      }
    }
  ]
};

marked.use(footnoteExtension);
marked.setOptions({ gfm: true, breaks: false });

function renderFootnoteSection() {
  if (footnoteRefs.size === 0) return '';
  const items = [];
  // Order by reference appearance
  const sortedIds = [...footnoteRefs.entries()].sort((a, b) => a[1] - b[1]);
  for (const [id, num] of sortedIds) {
    const def = footnoteDefs.get(id);
    if (!def) continue;
    const htmlText = marked.parseInline(def.text);
    items.push(`<li id="fn-${id}"><p>${htmlText} <a href="#fnref-${id}" aria-label="back to text">↩</a></p></li>`);
  }
  return `<section class="footnotes"><ol>${items.join('\n')}</ol></section>`;
}

// ---------- helpers ----------
function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

// Series registry: slug -> display label + full source name + author + keywords
const SERIES = {
  yuewei: {
    label: 'Notes from the Thatched Study',
    full: 'Notes from the Thatched Study (阅微草堂笔记)',
    author: 'Ji Yun (纪昀)',
    author_line: 'Ji Yun (纪昀, 1724–1805)',
    keywords: 'Ji Yun, Yuewei Caotang Biji, Qing dynasty, fox spirit, ghost story',
  },
  fengshen: {
    label: 'Investiture of the Gods',
    full: 'Investiture of the Gods (封神演义)',
    author: 'Xu Zhonglin (许仲琳)',
    author_line: 'Xu Zhonglin (许仲琳, Ming dynasty)',
    keywords: 'Fengshen Yanyi, Investiture of the Gods, Chinese mythology, Shang dynasty, Jiang Ziya',
  },
  xiyuan: {
    label: "The Coroner's Notebook",
    full: 'The Washing Away of Wrongs (洗冤集录)',
    author: 'Song Ci (宋慈)',
    author_line: 'Song Ci (宋慈, 1186–1249)',
    keywords: 'Song Ci, Xiyuan Jilu, forensic science, true crime, Song dynasty, coroner',
  },
  zibuyu: {
    label: 'What the Master Would Not Discuss',
    full: 'Zibuyu (子不语)',
    author: 'Yuan Mei (袁枚)',
    author_line: 'Yuan Mei (袁枚, 1716–1798)',
    keywords: 'Yuan Mei, Zibuyu, Qing dynasty, gothic horror, ghost story, supernatural',
  },
  jinghuayuan: {
    label: 'Flowers in the Mirror',
    full: 'Flowers in the Mirror (镜花缘)',
    author: 'Li Ruzhen (李汝珍)',
    author_line: 'Li Ruzhen (李汝珍, c. 1763–1830)',
    keywords: 'Li Ruzhen, Jinghua Yuan, Chinese fantasy, Country of Women, travelogue',
  },
  pinyaozhuan: {
    label: "Quelling the Demons' Revolt",
    full: "Quelling the Demons' Revolt (三遂平妖传)",
    author: 'Luo Guanzhong (罗贯中)',
    author_line: 'Luo Guanzhong (罗贯中, c. 1330–1400)',
    keywords: "Luo Guanzhong, Sansui Pingyao Zhuan, Chinese dark fantasy, demon revolt, Ming dynasty",
  },
  sanyan: {
    label: 'Sanyan: Stories of the Late Ming',
    full: 'Sanyan — Three Vernacular Story Collections (三言)',
    author: 'Feng Menglong (冯梦龙)',
    author_line: 'Feng Menglong (冯梦龙, 1574–1646), compiler',
    keywords: 'Feng Menglong, Sanyan, Stories Old and New, Stories to Caution the World, Stories to Awaken the World, Ming dynasty, vernacular fiction',
  },
  liaozhai: {
    label: 'Strange Tales from a Chinese Studio',
    full: 'Strange Tales from a Chinese Studio (聊斋志异)',
    author: 'Pu Songling (蒲松龄)',
    author_line: 'Pu Songling (蒲松龄, 1640–1715)',
    keywords: 'Pu Songling, Liaozhai Zhiyi, Strange Tales from a Chinese Studio, Qing dynasty, fox spirit, ghost story, classical Chinese tale',
  },
  soushen: {
    label: 'In Search of the Supernatural',
    full: 'In Search of the Supernatural (搜神记)',
    author: 'Gan Bao (干宝)',
    author_line: 'Gan Bao (干宝, c. 286–336)',
    keywords: 'Gan Bao, Soushen Ji, In Search of the Supernatural, Jin dynasty, Six Dynasties, zhiguai, supernatural, ghost story',
  },
  chuanqi: {
    label: 'Tang Tales of the Marvelous',
    full: 'Tang Tales of the Marvelous (唐传奇)',
    author: 'Various Tang Authors',
    author_line: 'Various Tang authors (7th–10th c.)',
    keywords: 'Tang chuanqi, Tang dynasty tales, classical Chinese romance, knight-errant, Tang marvels, Tang fiction',
  },
};

function getSeries(slug) {
  return SERIES[slug] || SERIES.yuewei; // default to yuewei for backwards compat
}

// ---------- HUB registry (v2.5 双轴主导航 2026-06-05) ----------
// hub frontmatter 字段必填且严格匹配 6 选 1；缺/拼错 → buildPost 抛错
// long_intro：每个 hub 的编辑性原创导读（HTML 多段，不 escape），见 ./_hub_long_intros.js
const HUB_LONG_INTROS = require('./_hub_long_intros');
const HUBS = [
  {
    key: 'Fox Spirits & Shapeshifters',
    slug: 'fox-spirits',
    nav_label: 'Foxes',
    h1: 'Chinese Fox Spirits & Shapeshifters',
    seo_title: 'Chinese Fox Spirits & Shapeshifters — Classical Tales in English | Cathay Tales',
    seo_description: 'Translated Chinese fox spirit tales — huli jing, fox widows, shapeshifters and the mortals who loved or feared them, from Tang dynasty to Qing.',
    keywords: 'Chinese fox spirits, huli jing, fox widow, shapeshifters, Chinese folklore, Pu Songling, Liaozhai, Ji Yun, fox wife',
    blurb: 'In Chinese folklore, the fox is the most famous shapeshifter — sometimes a seductress, sometimes a faithful wife, sometimes a Daoist apprentice on the road to immortality. These translated tales collect fox stories across centuries, from the cunning trickster of the Tang to the loyal fox widow of the Qing.',
  },
  {
    key: 'Love Across Death',
    slug: 'love-across-death',
    nav_label: 'Love & Death',
    h1: 'Chinese Tales of Love Across Death',
    seo_title: 'Chinese Ghost-Romance Tales: Love Across Death — Classical Stories in English | Cathay Tales',
    seo_description: 'Translated classical Chinese tales of love that survives death — ghost brides, returning lovers, vows that cross the grave. From Tang chuanqi to Qing strange tales.',
    keywords: 'Chinese ghost romance, ghost bride, ghost wife, love after death, Nie Xiaoqian, Chinese love story, chuanqi, undying love',
    blurb: 'No love story in classical China ends at the grave. Lovers return as ghosts to keep promises. Husbands and wives meet again across realms. The lines between the living and the dead were never the border Western readers might expect.',
  },
  {
    key: 'Karma & Retribution',
    slug: 'karma-and-retribution',
    nav_label: 'Karma',
    h1: 'Chinese Tales of Karma & Retribution',
    seo_title: 'Chinese Tales of Karma & Retribution — Classical Buddhist & Folk Stories in English | Cathay Tales',
    seo_description: 'Translated Chinese karma tales — past-life debts, reincarnation, animals who remember who you were, and the long arithmetic of right and wrong.',
    keywords: 'Chinese karma stories, Buddhist karma, reincarnation, past life, Chinese retribution tales, Ji Yun, Yuewei Caotang Biji, moral tales',
    blurb: 'In Chinese folk Buddhism, karma is not metaphor — it is a debt with interest. These tales trace what happens when the debt comes due across lifetimes: animals that remember past insults, neighbors who recognize old enemies, and the strange patience of moral arithmetic.',
  },
  {
    key: 'Afterlife & Underworld',
    slug: 'afterlife-and-underworld',
    nav_label: 'Afterlife',
    h1: 'Chinese Tales of the Afterlife & Underworld',
    seo_title: 'Chinese Afterlife & Underworld Tales — Classical Stories in English | Cathay Tales',
    seo_description: 'Translated Chinese underworld tales — courts of the dead, ghost magistrates, soul accounting, reincarnation queues, and the bureaucracy that even death cannot escape.',
    keywords: 'Chinese underworld, Chinese afterlife, Yama, Diyu, ghost magistrate, reincarnation, soul judgment, Chinese hell, bureaucracy of the dead',
    blurb: 'The Chinese underworld is not a place of pure punishment — it is a bureaucracy. Courts, ledgers, registers, magistrates. Souls queue. Officials file paperwork. These tales follow what happens when the world below behaves exactly like the world above.',
  },
  {
    key: 'Hauntings & Ghost Encounters',
    slug: 'hauntings',
    nav_label: 'Hauntings',
    h1: 'Chinese Hauntings & Ghost Encounters',
    seo_title: 'Chinese Ghost Stories: Hauntings & Encounters — Classical Tales in English | Cathay Tales',
    seo_description: 'Translated Chinese ghost-encounter tales — haunted temples, faces in the wall, late-night visitors, and the scholars who chose to keep reading anyway.',
    keywords: 'Chinese ghost stories, Chinese hauntings, ghost encounter, scholar and ghost, haunted house, Ji Yun, Pu Songling, Yuan Mei, fearless scholar',
    blurb: 'Not every Chinese ghost wants revenge. Some just want a candle, a chat, or to be left alone. These translated tales collect the country\'s long catalogue of strange encounters — and the scholars, monks, and ordinary householders who learned to live next door to the dead.',
  },
  {
    key: 'Taoist Marvels',
    slug: 'taoist-marvels',
    nav_label: 'Tao',
    h1: 'Chinese Tales of Taoist Marvels',
    seo_title: 'Chinese Taoist Marvels — Classical Immortal & Magic Tales in English | Cathay Tales',
    seo_description: 'Translated Chinese tales of Taoist marvels — immortals, alchemists, mountain hermits, talismans, sword-flying masters, and the long apprenticeship to the Way.',
    keywords: 'Chinese Taoist tales, xian, immortal, Chinese alchemy, mountain hermit, talisman, Taoist magic, Dao, qi cultivation, xiuzhen',
    blurb: 'Long before xianxia, classical China was full of Taoist marvels — apprentices who learned to walk through walls, hermits who flew swords across mountains, alchemists who paid for immortality in years of their own lives. These tales translate the originals.',
  },
];

const HUB_BY_KEY = Object.fromEntries(HUBS.map(h => [h.key, h]));

function getHub(key) {
  if (!key) return null;
  const h = HUB_BY_KEY[key];
  if (!h) {
    throw new Error(
      `Unknown hub "${key}". Allowed: ${HUBS.map(x => x.key).join(' | ')}`
    );
  }
  return h;
}

// 朝代→标准化显示（接受 "Qing" / "Qing dynasty" / "qing" 都标准化为 "Qing dynasty"）
function normalizeDynasty(raw) {
  if (!raw) return null;
  const s = String(raw).trim();
  if (/^(multi-?era|mythic)$/i.test(s)) {
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  }
  // 去掉末尾 "dynasty"，规范首字母大写
  const core = s.replace(/\s+dynasty$/i, '').trim();
  const normalized = core.charAt(0).toUpperCase() + core.slice(1).toLowerCase();
  // 特殊：Six Dynasties / Five Dynasties 保留两词
  if (/^(six|five)$/i.test(core)) {
    return `${normalized} Dynasties`;
  }
  return `${normalized} dynasty`;
}

// 字数→难度 chip（不依赖 frontmatter，按正文 markdown 字数自动算）
function computeDifficulty(bodyMarkdown) {
  // 简单去 frontmatter 残留+标题计数，按空白分词
  const text = bodyMarkdown
    .replace(/```[\s\S]*?```/g, ' ')       // 代码块剔除
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')  // 图片
    .replace(/\[\^[^\]]+\]/g, ' ')          // 脚注引用
    .replace(/[#*_>`~\-]+/g, ' ');          // markdown 符号
  const words = text.split(/\s+/).filter(w => /[A-Za-z]/.test(w));
  const n = words.length;
  if (n <= 1500) return { word_count: n, emoji: '🟢', label: 'short read', minutes: '~5 min' };
  if (n <= 3500) return { word_count: n, emoji: '🟡', label: 'medium read', minutes: '~10 min' };
  return { word_count: n, emoji: '🔴', label: 'long read', minutes: '~20 min+' };
}

// HTML 转义（用于 attr/text content）
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// 丛书跳锚点（暂未做独立 series 页，先跳 index 的 About 段；后续可扩 /series/{slug}.html）
function seriesAnchor(seriesSlug) {
  return `../index.html#series-list`;
}

// 渲染 hub 双轴主导航（第一行 6 hub，第二行 utility）
// pathPrefix: "" for /index.html /hubs /static 同级；"../" for /posts/* /hubs/*
function renderHubNav(pathPrefix = '') {
  const p = pathPrefix;
  const hubLinks = HUBS.map(h =>
    `        <a href="${p}hubs/${h.slug}.html">${escapeHtml(h.nav_label)}</a>`
  ).join('\n');
  return `<nav class="site-nav" aria-label="Main navigation">
      <div class="nav-hubs" aria-label="Tale themes">
${hubLinks}
      </div>
      <div class="nav-utility" aria-label="Site pages">
        <a href="${p}index.html">All Tales</a>
        <a href="${p}about.html">About</a>
        <a href="${p}index.html#subscribe">Subscribe</a>
        <a href="${p}contact.html">Contact</a>
      </div>
    </nav>`;
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

function applyTemplate(template, vars) {
  let out = template;
  for (const [k, v] of Object.entries(vars)) {
    out = out.replaceAll(`{{${k}}}`, v ?? '');
  }
  return out;
}

// ---------- build ----------
function buildPost(filePath, template) {
  resetFootnotes();
  const raw = fs.readFileSync(filePath, 'utf8');
  const { data: meta, content } = matter(raw);

  // Render body
  const bodyHtml = marked.parse(content);
  const footnotesHtml = renderFootnoteSection();

  // ---- Inject hover tooltips into footnote refs ----
  let bodyWithTooltips = bodyHtml;
  for (const [id, def] of footnoteDefs.entries()) {
    const inlineHtml = marked.parseInline(def.text);
    const plain = inlineHtml
      .replace(/<[^>]+>/g, '')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/\s+/g, ' ')
      .trim();
    const truncated = plain.length > 320 ? plain.slice(0, 317) + '...' : plain;
    const titleAttr = truncated
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    const safeId = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    bodyWithTooltips = bodyWithTooltips
      .replace(
        new RegExp(`<a href="#fn-${safeId}" data-fn-id="${safeId}">`, 'g'),
        `<a href="#fn-${id}" data-fn-id="${id}" title="${titleAttr}">`
      )
      .replace(
        new RegExp(`<span class="footnote-tooltip" data-fn-id="${safeId}"></span>`, 'g'),
        `<span class="footnote-tooltip" data-fn-id="${id}">${inlineHtml}</span>`
      );
  }

  let fullContent = bodyWithTooltips + footnotesHtml;

  // ---- Cleanup: strip empty headings + adjacent <hr> pair ----
  fullContent = fullContent
    .replace(/<hr>\s*<h2[^>]*>\s*Annotations\s*<\/h2>\s*<hr>/gi, '<hr>')
    .replace(/<h([1-6])[^>]*>\s*<\/h\1>/g, '')
    .replace(/(<hr>\s*){2,}/g, '<hr>');

  const cleanedContent = fullContent;

  const outName = `${meta.slug}.html`;
  const tags = (meta.tags || []).join(', ');
  const titleBilingual = meta.title_zh ? `${meta.title} / ${meta.title_zh}` : meta.title;
  const series = getSeries(meta.series);

  // ---- v2.5 hub/dynasty/difficulty 校验+派生 ----
  if (!meta.hub) {
    throw new Error(
      `[${meta.slug}] frontmatter.hub 缺失（v2.5 双轴主导航铁律），必填 6 hub 之一：\n  ${HUBS.map(h => h.key).join('\n  ')}`
    );
  }
  if (!meta.dynasty) {
    throw new Error(
      `[${meta.slug}] frontmatter.dynasty 缺失（v2.5 必填），如 Tang / Song / Ming / Qing / Multi-era / Mythic`
    );
  }
  const hub = getHub(meta.hub);
  const dynastyLabel = normalizeDynasty(meta.dynasty);
  const diff = computeDifficulty(content);

  // chip 一行：Hub · 朝代 · 难度 · 丛书
  const chipHtml = `
    <nav class="post-chips" aria-label="Tale categories">
      <a class="chip chip-hub" href="../hubs/${hub.slug}.html">${escapeHtml(hub.nav_label)}</a>
      <span class="chip chip-dynasty">${escapeHtml(dynastyLabel)}</span>
      <span class="chip chip-difficulty">${diff.emoji} ${diff.label} (${diff.minutes})</span>
      <a class="chip chip-series" href="${seriesAnchor(meta.series)}">${escapeHtml(series.label)}</a>
    </nav>`;

  // chip 注入：把 chip 放在第一个 </h1> 之后（精确定位到正文标题下）
  let contentWithChips = cleanedContent;
  const h1CloseRe = /<\/h1>/;
  if (h1CloseRe.test(contentWithChips)) {
    contentWithChips = contentWithChips.replace(h1CloseRe, '</h1>\n' + chipHtml);
  } else {
    // 没 H1 兜底：前置
    contentWithChips = chipHtml + '\n' + contentWithChips;
  }

  const html = applyTemplate(template, {
    TITLE: titleBilingual,
    SEO_DESCRIPTION: meta.seo_description || meta.excerpt || '',
    TAGS: tags,
    DATE: meta.date,
    DATE_FORMATTED: formatDate(meta.date),
    TALE_NUMBER: meta.tale_number || '?',
    CONTENT: contentWithChips,
    POST_CHIPS: chipHtml,
    HUB_NAV: renderHubNav('../'),
    SERIES_LABEL: series.label,
    SERIES_LABEL_FULL: series.full,
    SERIES_KEYWORDS: series.keywords,
    AUTHOR_NAME: series.author,
    AUTHOR_LINE: series.author_line,
    CSS_PATH: '../assets/style.css',
    HOME_PATH: '../index.html',
    ASSETS_BASE: '../assets/',
  });

  fs.writeFileSync(path.join(DIST_POSTS_DIR, outName), html);
  return {
    ...meta,
    outPath: `posts/${outName}`,
    bodyHtml: cleanedContent,
    hub_obj: hub,
    dynasty_label: dynastyLabel,
    difficulty: diff,
  };
}

function buildIndex(posts, template) {
  // 倒序：最新发布的在最前；同日按文件名（数字前缀）倒序作 tiebreaker
  const sorted = [...posts].sort((a, b) => {
    const d = new Date(b.date) - new Date(a.date);
    return d !== 0 ? d : (b.outPath || '').localeCompare(a.outPath || '');
  });
  const cards = sorted.map(p => {
    const titleHtml = p.title_zh
      ? `${p.title} <span class="title-zh">/ ${p.title_zh}</span>`
      : p.title;
    return `
    <article class="tale-card">
      <a href="${p.outPath}">
        <div class="meta">${formatDate(p.date)}</div>
        <h3>${titleHtml}</h3>
        <p class="excerpt">${p.excerpt || ''}</p>
      </a>
    </article>
  `;
  }).join('');

  // hub 入口区：6 张大卡片
  const hubEntries = HUBS.map(h => {
    const count = posts.filter(p => p.hub_obj && p.hub_obj.key === h.key).length;
    const countLabel = count === 0
      ? '<span class="hub-count hub-count-empty">coming soon</span>'
      : `<span class="hub-count">${count} tale${count === 1 ? '' : 's'}</span>`;
    return `
    <a class="hub-card" href="hubs/${h.slug}.html">
      <div class="hub-card-head">
        <span class="hub-card-label">${escapeHtml(h.nav_label)}</span>
        ${countLabel}
      </div>
      <h3 class="hub-card-title">${escapeHtml(h.h1.replace(/^Chinese (Tales of |Hauntings & |Fox |Taoist )/i, m => m))}</h3>
      <p class="hub-card-blurb">${escapeHtml(h.blurb)}</p>
    </a>`;
  }).join('');

  const hubEntriesHtml = `
    <section class="hubs-section">
      <h2>Browse by theme</h2>
      <p class="hubs-section-lead">Six themed hubs gather tales across centuries — pick one to follow a single thread of Chinese folklore.</p>
      <div class="hub-grid">${hubEntries}
      </div>
    </section>`;

  let html = template.replace('{{TALE_LIST}}', cards);
  html = html.replace('{{HUB_NAV}}', renderHubNav(''));
  html = html.replace('{{HUB_ENTRIES}}', hubEntriesHtml);
  fs.writeFileSync(path.join(DIST_DIR, 'index.html'), html);
}

function buildHubs(posts, template) {
  ensureDir(DIST_HUBS_DIR);
  for (const hub of HUBS) {
    const inHub = posts
      .filter(p => p.hub_obj && p.hub_obj.key === hub.key)
      .sort((a, b) => new Date(b.date) - new Date(a.date));

    let cards;
    if (inHub.length === 0) {
      cards = `
      <p class="hub-empty">
        No tales translated for this hub yet — new ones are added weekly.
        In the meantime, <a href="../index.html">browse all tales</a> or
        <a href="../index.html#subscribe">subscribe</a> to hear when this hub opens.
      </p>`;
    } else {
      cards = inHub.map(p => {
        const titleHtml = p.title_zh
          ? `${escapeHtml(p.title)} <span class="title-zh">/ ${escapeHtml(p.title_zh)}</span>`
          : escapeHtml(p.title);
        const chipLine = `
          <span class="hub-card-chip chip-dynasty">${escapeHtml(p.dynasty_label)}</span>
          <span class="hub-card-chip chip-difficulty">${p.difficulty.emoji} ${p.difficulty.label}</span>`;
        return `
      <article class="tale-card hub-tale-card">
        <a href="../${p.outPath}">
          <div class="meta">${formatDate(p.date)}</div>
          <h3>${titleHtml}</h3>
          <div class="hub-card-chips">${chipLine}
          </div>
          <p class="excerpt">${escapeHtml(p.excerpt || '')}</p>
        </a>
      </article>`;
      }).join('');
    }

    const html = applyTemplate(template, {
      HUB_KEY: escapeHtml(hub.key),
      HUB_NAV_LABEL: escapeHtml(hub.nav_label),
      HUB_H1: escapeHtml(hub.h1),
      HUB_SEO_TITLE: escapeHtml(hub.seo_title),
      HUB_SEO_DESCRIPTION: escapeHtml(hub.seo_description),
      HUB_KEYWORDS: escapeHtml(hub.keywords),
      HUB_BLURB: escapeHtml(hub.blurb),
      HUB_LONG_INTRO: HUB_LONG_INTROS[hub.slug] || '',
      HUB_SLUG: hub.slug,
      HUB_CARDS: cards,
      HUB_COUNT: inHub.length,
      HUB_NAV: renderHubNav('../'),
      CSS_PATH: '../assets/style.css',
      HOME_PATH: '../index.html',
      ASSETS_BASE: '../assets/',
    });
    fs.writeFileSync(path.join(DIST_HUBS_DIR, `${hub.slug}.html`), html);
  }
}

function copyAssets() {
  ensureDir(DIST_ASSETS_DIR);
  for (const file of fs.readdirSync(ASSETS_DIR)) {
    fs.copyFileSync(path.join(ASSETS_DIR, file), path.join(DIST_ASSETS_DIR, file));
  }
}

function copyStatic() {
  if (!fs.existsSync(STATIC_DIR)) return;
  for (const file of fs.readdirSync(STATIC_DIR)) {
    const src = path.join(STATIC_DIR, file);
    if (fs.statSync(src).isFile()) {
      fs.copyFileSync(src, path.join(DIST_DIR, file));
    }
  }
}

const SITE_URL = 'https://cathaytales.com';

function buildSitemap(posts) {
  const today = new Date().toISOString().slice(0, 10);
  const urls = [
    { loc: `${SITE_URL}/`, lastmod: today, priority: '1.0' },
    { loc: `${SITE_URL}/about.html`, lastmod: today, priority: '0.7' },
    { loc: `${SITE_URL}/contact.html`, lastmod: today, priority: '0.5' },
    { loc: `${SITE_URL}/privacy.html`, lastmod: today, priority: '0.3' },
    ...HUBS.map(h => ({
      loc: `${SITE_URL}/hubs/${h.slug}`,
      lastmod: today,
      priority: '0.9',
    })),
    ...posts.map(p => ({
      loc: `${SITE_URL}/${p.outPath.replace(/\.html$/, '')}`,
      lastmod: p.date,
      priority: '0.8',
    })),
  ];
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(u => `  <url>
    <loc>${u.loc}</loc>
    <lastmod>${u.lastmod}</lastmod>
    <priority>${u.priority}</priority>
  </url>`).join('\n')}
</urlset>
`;
  fs.writeFileSync(path.join(DIST_DIR, 'sitemap.xml'), xml);
}

function buildRobots() {
  const txt = `User-agent: *
Allow: /

Sitemap: ${SITE_URL}/sitemap.xml
`;
  fs.writeFileSync(path.join(DIST_DIR, 'robots.txt'), txt);
}

function escapeXml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function buildRSS(posts) {
  // Newest first, cap at latest 20 to keep feed lean
  const sorted = [...posts].sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 20);
  const buildDate = new Date().toUTCString();
  const items = sorted.map(p => {
    const url = `${SITE_URL}/${p.outPath.replace(/\.html$/, '')}`;
    const pubDate = new Date(p.date).toUTCString();
    const titleBilingual = p.title_zh ? `${p.title} / ${p.title_zh}` : p.title;
    const series = getSeries(p.series);
    const categories = [series.label, ...(p.tags || [])]
      .map(t => `      <category>${escapeXml(t)}</category>`)
      .join('\n');
    // content:encoded gets full body HTML so Beehiiv can build complete email
    return `    <item>
      <title>${escapeXml(titleBilingual)}</title>
      <link>${url}</link>
      <guid isPermaLink="true">${url}</guid>
      <pubDate>${pubDate}</pubDate>
      <dc:creator>${escapeXml(series.author)}</dc:creator>
${categories}
      <description>${escapeXml(p.excerpt || '')}</description>
      <content:encoded><![CDATA[${p.bodyHtml || ''}]]></content:encoded>
    </item>`;
  }).join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Cathay Tales</title>
    <link>${SITE_URL}</link>
    <description>Classical Chinese tales — fox spirits, ghosts, gods, and forensic cases — retold in plain English with light commentary.</description>
    <language>en-us</language>
    <lastBuildDate>${buildDate}</lastBuildDate>
    <atom:link href="${SITE_URL}/feed.xml" rel="self" type="application/rss+xml" />
    <generator>cathaytales build.js</generator>
${items}
  </channel>
</rss>
`;
  fs.writeFileSync(path.join(DIST_DIR, 'feed.xml'), xml);
}

function main() {
  ensureDir(DIST_DIR);
  ensureDir(DIST_POSTS_DIR);
  ensureDir(DIST_HUBS_DIR);
  copyAssets();
  copyStatic();

  const postTemplate = fs.readFileSync(path.join(TEMPLATES_DIR, 'post.html'), 'utf8');
  const indexTemplate = fs.readFileSync(path.join(TEMPLATES_DIR, 'index.html'), 'utf8');
  const hubTemplate = fs.readFileSync(path.join(TEMPLATES_DIR, 'hub.html'), 'utf8');

  const postFiles = fs.readdirSync(POSTS_DIR).filter(f => f.endsWith('.md'));
  const posts = postFiles.map(f => buildPost(path.join(POSTS_DIR, f), postTemplate));

  buildIndex(posts, indexTemplate);
  buildHubs(posts, hubTemplate);
  buildSitemap(posts);
  buildRobots();
  buildRSS(posts);

  console.log(`✓ Built ${posts.length} post(s) + ${HUBS.length} hub(s)`);
  console.log(`✓ Output: ${DIST_DIR}`);
}

main();
