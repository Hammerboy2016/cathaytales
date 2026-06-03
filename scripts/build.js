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
};

function getSeries(slug) {
  return SERIES[slug] || SERIES.yuewei; // default to yuewei for backwards compat
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

  const html = applyTemplate(template, {
    TITLE: titleBilingual,
    SEO_DESCRIPTION: meta.seo_description || meta.excerpt || '',
    TAGS: tags,
    DATE: meta.date,
    DATE_FORMATTED: formatDate(meta.date),
    TALE_NUMBER: meta.tale_number || '?',
    CONTENT: cleanedContent,
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
  return { ...meta, outPath: `posts/${outName}` };
}

function buildIndex(posts, template) {
  const sorted = posts.sort((a, b) => (a.tale_number || 0) - (b.tale_number || 0));
  const cards = sorted.map(p => {
    const titleHtml = p.title_zh
      ? `${p.title} <span class="title-zh">/ ${p.title_zh}</span>`
      : p.title;
    return `
    <article class="tale-card">
      <a href="${p.outPath}">
        <div class="meta">Tale ${p.tale_number || '?'} · ${formatDate(p.date)}</div>
        <h3>${titleHtml}</h3>
        <p class="excerpt">${p.excerpt || ''}</p>
      </a>
    </article>
  `;
  }).join('');

  const html = template.replace('{{TALE_LIST}}', cards);
  fs.writeFileSync(path.join(DIST_DIR, 'index.html'), html);
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
  const urls = [
    { loc: `${SITE_URL}/`, lastmod: new Date().toISOString().slice(0, 10), priority: '1.0' },
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

function main() {
  ensureDir(DIST_DIR);
  ensureDir(DIST_POSTS_DIR);
  copyAssets();
  copyStatic();

  const postTemplate = fs.readFileSync(path.join(TEMPLATES_DIR, 'post.html'), 'utf8');
  const indexTemplate = fs.readFileSync(path.join(TEMPLATES_DIR, 'index.html'), 'utf8');

  const postFiles = fs.readdirSync(POSTS_DIR).filter(f => f.endsWith('.md'));
  const posts = postFiles.map(f => buildPost(path.join(POSTS_DIR, f), postTemplate));

  buildIndex(posts, indexTemplate);
  buildSitemap(posts);
  buildRobots();

  console.log(`✓ Built ${posts.length} post(s)`);
  console.log(`✓ Output: ${DIST_DIR}`);
}

main();
