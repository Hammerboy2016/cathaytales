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
        return `<sup class="footnote-ref" id="fnref-${token.id}"><a href="#fn-${token.id}">[${num}]</a></sup>`;
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
  const fullContent = bodyHtml + footnotesHtml;

  const outName = `${meta.slug}.html`;
  const tags = (meta.tags || []).join(', ');

  const html = applyTemplate(template, {
    TITLE: meta.title,
    SEO_DESCRIPTION: meta.seo_description || meta.excerpt || '',
    TAGS: tags,
    DATE: meta.date,
    DATE_FORMATTED: formatDate(meta.date),
    TALE_NUMBER: meta.tale_number || '?',
    CONTENT: fullContent,
    CSS_PATH: '../assets/style.css',
    HOME_PATH: '../index.html',
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

function main() {
  ensureDir(DIST_DIR);
  ensureDir(DIST_POSTS_DIR);
  copyAssets();

  const postTemplate = fs.readFileSync(path.join(TEMPLATES_DIR, 'post.html'), 'utf8');
  const indexTemplate = fs.readFileSync(path.join(TEMPLATES_DIR, 'index.html'), 'utf8');

  const postFiles = fs.readdirSync(POSTS_DIR).filter(f => f.endsWith('.md'));
  const posts = postFiles.map(f => buildPost(path.join(POSTS_DIR, f), postTemplate));

  buildIndex(posts, indexTemplate);

  console.log(`✓ Built ${posts.length} post(s)`);
  console.log(`✓ Output: ${DIST_DIR}`);
}

main();
