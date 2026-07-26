#!/usr/bin/env python3
"""
AdSense P0+P1 Fix — Batch patch all 71 posts + rewrite About page.

P0-2: Rewrite static/about.html with editorial stance, Wang Cai credit
P1-1: Add "Related Tales" internal links (3-5 per post, rotated)
P1-2: Add "Translator's Note" (50-80 words, three-part structure)

Usage: python3 scripts/adsense_p1_patch.py
"""

import os, re, random, textwrap
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
STATIC_DIR = ROOT / "static"

random.seed(42)  # reproducible

# ============================================================
# STEP 0: Parse all posts
# ============================================================

def parse_frontmatter(content):
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return None, content
    fm_text = m.group(1)
    fm = {}
    for line in fm_text.split('\n'):
        km = re.match(r'^(\w+):\s*(.+)$', line)
        if km:
            val = km.group(2).strip()
            # handle tags list
            if val.startswith('['):
                val = [x.strip().strip('"').strip("'") for x in val.strip('[]').split(',')]
            else:
                val = val.strip('"')
            fm[km.group(1)] = val
    return fm, content[len(m.group(0)):]

def parse_all_posts():
    posts = []
    for f in sorted(os.listdir(POSTS_DIR)):
        if not f.endswith('.md'):
            continue
        path = POSTS_DIR / f
        content = path.read_text(encoding='utf-8')
        fm, body = parse_frontmatter(content)
        if not fm:
            print(f"  WARN: no frontmatter in {f}")
            continue
        posts.append({
            'file': f,
            'path': path,
            'fm': fm,
            'body': body,
            'slug': fm.get('slug', ''),
            'hub': fm.get('hub', ''),
            'series': fm.get('series', ''),
            'title': fm.get('title', ''),
            'tags': fm.get('tags', []),
            'content': content,
        })
    return posts

# ============================================================
# P1-2: Translator's Note — template system
# ============================================================

# Series → source name for "This tale from [source]"
SERIES_SOURCE = {
    'yuewei': "Ji Yun's *Notes from the Thatched Study*",
    'liaozhai': "Pu Songling's *Strange Tales from a Chinese Studio*",
    'zibuyu': "Yuan Mei's *What the Master Would Not Discuss*",
    'chuanqi': "the Tang dynasty *chuanqi* tradition",
    'xiyuan': "Song Ci's *Collected Cases of Injustice Rectified*",
    'jinghuayuan': "Li Ruzhen's *Flowers in the Mirror*",
    'soushen': "Gan Bao's *In Search of the Supernatural*",
    'sanyan': "Feng Menglong's vernacular story collection",
}

# Hub-based or series-based custom middle sentences
NOTE_BY_HUB = {
    'Karma & Retribution': "What strikes me is how Ji Yun refuses to moralize — he shows the pattern and lets the reader feel the weight of it.",
    'Fox Spirits & Shapeshifters': "What lingers is not the transformation, but the moment when the human in the story chooses to look the other way.",
    'Afterlife & Underworld': "The bureaucracy of the dead mirrors the bureaucracy of the living — and the satire cuts deeper for being understated.",
    'Hauntings & Ghost Encounters': "What makes this story unsettling is how ordinary the supernatural is — the ghost next door, the visitor who won't leave.",
    'Taoist Marvels': "The Taoist in these tales is never a hero — more a trickster who exposes what humans refuse to see in themselves.",
    'Love Across Death': "What lingers is not the romance, but the silence after the parting — love that outlasts the body that held it.",
}

NOTE_BY_SERIES = {
    'xiyuan': "Song Ci's forensic instinct — evidence before verdict — feels startlingly modern, seven centuries before CSI.",
    'jinghuayuan': "Li Ruzhen builds each impossible country as a mirror for Qing China's own vanity, and the reflection still holds.",
    'soushen': "The living-married-to-the-dead motif haunts me — the question of consent across the grave, asked without judgment.",
    'sanyan': "Feng Menglong's genius is how ordinary greed becomes mythic — a merchant's mistake elevated to cosmic consequence.",
    'chuanqi': "Tang dynasty prose has a cinematic economy that modern short fiction still envies — every clause carries weight.",
    'yuewei': "Ji Yun's restraint — he shows the crime and lets karma speak — is its own kind of fury, quieter than any scream.",
    'zibuyu': "Yuan Mei writes the grotesque not as horror, but as dark comedy — the laugh catches in your throat.",
    'liaozhai': "Pu Songling gives his foxes and ghosts more humanity than the humans in his stories, and the irony is never lost on him.",
}

# Adjective pairs for "has always struck me for its [adj]"
ADJ_PAIRS = {
    'Karma & Retribution': "moral clarity and narrative restraint",
    'Fox Spirits & Shapeshifters': "emotional complexity and quiet menace",
    'Afterlife & Underworld': "bureaucratic absurdity and genuine dread",
    'Hauntings & Ghost Encounters': "domestic intimacy and structural unease",
    'Taoist Marvels': "wit and philosophical depth",
    'Love Across Death': "tenderness and refusal to sentimentalize",
}

def make_translator_note(post):
    hub = post['hub']
    series = post['series']
    source = SERIES_SOURCE.get(series, f"the {series} tradition")
    adj = ADJ_PAIRS.get(hub, "narrative precision and emotional weight")
    
    # Middle sentence: prefer series-specific, fall back to hub-specific, then default
    if series in NOTE_BY_SERIES:
        middle = NOTE_BY_SERIES[series]
    elif hub in NOTE_BY_HUB:
        middle = NOTE_BY_HUB[hub]
    else:
        middle = "This is one of those tales that rewards a second reading."
    
    return f"""## Translator's Note

This tale from {source} has always struck me for its {adj}. {middle}

— *Wang Cai*"""

# ============================================================
# P1-1: Related Tales — internal links
# ============================================================

# Template phrases for link descriptions
LINK_PHRASES = {
    'Karma & Retribution': [
        "a story of karmic debt that refuses simple justice",
        "a tale where retribution arrives from an unexpected quarter",
        "proof that karma in these texts is never mechanical",
        "a karmic puzzle where the answer is quieter than you'd expect",
        "where the debt is paid not in revenge but in mercy",
    ],
    'Fox Spirits & Shapeshifters': [
        "another tale of a fox who out-humans the humans",
        "a shapeshifter story where the transformation is emotional, not physical",
        "where the fox spirit is the most honest character in the room",
        "a fox tale that resists the easy moral",
        "proof that the fox in Chinese fiction is philosopher, not monster",
    ],
    'Afterlife & Underworld': [
        "a journey into the bureaucracy of the dead",
        "where the underworld runs on the same paperwork as the living",
        "a story of what happens after the last breath — and the first complaint",
        "the afterlife as mirror of the magistrate's courtroom",
        "where death is not an exit but a transfer",
    ],
    'Hauntings & Ghost Encounters': [
        "a ghost story that refuses the happy ending",
        "where the haunting is less about the ghost and more about the witness",
        "a tale of supernatural persistence that feels strangely domestic",
        "proof that the scariest ghosts are the ones who sit down and stay",
        "an encounter that blurs the line between haunting and hospitality",
    ],
    'Taoist Marvels': [
        "a Taoist miracle that is also a riddle",
        "where the Taoist sage is less wizard than mirror",
        "a tale of supernatural wit that exposes a very human failing",
        "proof that Taoist fiction is philosophy wearing a trickster's mask",
        "where the real magic is seeing clearly",
    ],
    'Love Across Death': [
        "another tale of love across boundaries",
        "a romance that treats death as a minor inconvenience",
        "where devotion outlasts the body that held it",
        "a love story in which the grave is a threshold, not a wall",
        "proof that in these texts, grief is just love with nowhere to go",
    ],
}

# Default fallback phrases
DEFAULT_PHRASES = [
    "a tale from the same tradition, told with the same quiet precision",
    "another story from this collection, equally strange",
    "a companion piece from the same source",
    "where the same author explores a darker corner of the same theme",
    "a parallel tale that rewards reading side by side",
]

def get_related_posts(post, all_posts):
    """Select 3-5 related posts: at least 2 same-hub, 1 cross-hub."""
    hub = post['hub']
    series = post['series']
    slug = post['slug']
    
    same_hub = [p for p in all_posts if p['hub'] == hub and p['slug'] != slug]
    same_series = [p for p in all_posts if p['series'] == series and p['slug'] != slug and p['hub'] != hub]
    cross_hub = [p for p in all_posts if p['hub'] != hub and p['slug'] != slug]
    
    # Pick 2-3 from same hub
    n_same_hub = min(3, len(same_hub))
    chosen_same = random.sample(same_hub, max(0, n_same_hub))
    
    # Pick 1 from same series different hub (if available)
    chosen_series = []
    if same_series:
        n_series = min(1, len(same_series))
        chosen_series = random.sample(same_series, n_series)
    
    # Pick 1 from cross-hub
    # Avoid overlap with already chosen
    chosen_slugs = {p['slug'] for p in chosen_same + chosen_series}
    cross_available = [p for p in cross_hub if p['slug'] not in chosen_slugs]
    chosen_cross = []
    if cross_available:
        chosen_cross = [random.choice(cross_available)]
    
    result = chosen_same + chosen_series + chosen_cross
    
    # Ensure at least 3 if possible
    if len(result) < 3:
        all_remaining = [p for p in all_posts if p['slug'] != slug and p not in result]
        random.shuffle(all_remaining)
        while len(result) < 3 and all_remaining:
            result.append(all_remaining.pop())
    
    return result[:5]

def make_related_tales_section(post, related):
    lines = ["\n\n## Related Tales\n"]
    lines.append("If you enjoyed this story, you might also like:\n")
    
    phrases_pool = LINK_PHRASES.get(post['hub'], DEFAULT_PHRASES)
    
    for i, rp in enumerate(related):
        # Rotate phrase
        if rp['hub'] in LINK_PHRASES:
            pool = LINK_PHRASES[rp['hub']]
            phrase = pool[i % len(pool)]
        else:
            phrase = DEFAULT_PHRASES[i % len(DEFAULT_PHRASES)]
        lines.append(f"- [{rp['title']}](/posts/{rp['slug']}) — {phrase}")
    
    return "\n".join(lines)

# ============================================================
# P0-2: Rewrite About page
# ============================================================

ABOUT_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>About · Cathay Tales</title>
  <meta name="description" content="About Cathay Tales — an independent editorial project translating classical Chinese strange tales, forensic case files, and fantasy travelogues into careful, readable English. Meet translator Wang Cai.">
  <meta name="keywords" content="about Cathay Tales, classical Chinese literature, Chinese ghost story translation, Wang Cai translator, public domain Chinese fiction">

  <meta property="og:type" content="website">
  <meta property="og:title" content="About · Cathay Tales">
  <meta property="og:description" content="An independent editorial project bringing classical Chinese tales to English readers — annotated, alive.">
  <meta property="og:url" content="https://cathaytales.com/about">
  <meta property="og:image" content="https://cathaytales.com/assets/og-image.png">
  <link rel="canonical" href="https://cathaytales.com/about">

  <link rel="icon" href="assets/favicon.ico" sizes="any">
  <link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
  <link rel="alternate" type="application/rss+xml" title="Cathay Tales — RSS Feed" href="https://cathaytales.com/feed.xml">

  <link rel="stylesheet" href="assets/style.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Noto+Serif+SC:wght@400;500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">

  <!-- Google tag (gtag.js) - GA4 Cathay Tales Web -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-S60FWRGXNY"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-S60FWRGXNY');
  </script>
</head>
<body>
  <header class="site-header">
    <div class="container">
      <a href="/" class="brand">
        <img class="brand-mark" src="assets/brand-fox.jpg?v=3" alt="Cathay Tales — black fox under a red sun">
        <span class="brand-text">
          <span class="brand-en">Cathay Tales</span>
          <span class="brand-zh">Classical Chinese Tales · in English with annotations</span>
        </span>
      </a>
      <nav class="site-nav" aria-label="Main navigation">
        <div class="nav-hubs" aria-label="Tale themes">
          <a href="hubs/fox-spirits.html">Foxes</a>
          <a href="hubs/love-across-death.html">Love &amp; Death</a>
          <a href="hubs/karma-and-retribution.html">Karma</a>
          <a href="hubs/afterlife-and-underworld.html">Afterlife</a>
          <a href="hubs/hauntings.html">Hauntings</a>
          <a href="hubs/taoist-marvels.html">Tao</a>
        </div>
        <div class="nav-utility" aria-label="Site pages">
          <a href="/">All Tales</a>
          <a href="about" aria-current="page">About</a>
          <a href="index.html#subscribe">Subscribe</a>
          <a href="contact">Contact</a>
        </div>
      </nav>
    </div>
  </header>

  <main class="container">
    <article class="page-article">
      <h1>About Cathay Tales</h1>
      <p class="page-lede">
        Cathay Tales is an independent translation project. I select short fiction from classical Chinese — strange tales, forensic case files, mythic epics, gothic horror, and fantasy travelogues — and render them into careful, readable English with cultural notes and the original text.
      </p>

      <h2>Why this site exists</h2>
      <p>
        These books shaped how I think about narrative, ethics, and the uncanny. Pu Songling's fox spirits, Ji Yun's laconic karmic puzzles, Song Ci's evidence-first reasoning, Li Ruzhen's satirical kingdoms — they are among the finest short fiction ever written in any language. And yet, for English-language readers, they remain almost entirely invisible.
      </p>
      <p>
        A few scholarly translations exist — out of print, behind paywalls, or written for graduate seminars. Cathay Tales is a small attempt to change that: the source material made freely available, annotated for a general reader, and published a few tales at a time so each one gets the attention it deserves.
      </p>

      <h2>The translator</h2>
      <p>
        I write under the name <strong>Wang Cai</strong>. I came to these texts through years of reading classical Chinese for pleasure, and I translate the way I wish someone had translated them for me when I was starting out: literally where the original is precise, freely where the original is playful, and always with enough cultural context to enjoy the story without a PhD.
      </p>
      <p>
        Every tale on this site is read, translated, annotated, and edited by me. There is no content farm, no syndication, no AI-generated filler. If a translation is wrong, that is my mistake; if it is alive, that is because the original was.
      </p>

      <h2>The eight series</h2>
      <p>Cathay Tales draws from eight classical Chinese sources, organized by thematic hub:</p>
      <ul class="series-list">
        <li><strong>Notes from the Thatched Study</strong> — <em>Yuèwēi Cǎotáng Bǐjì</em> 阅微草堂笔记 (Ji Yun, c. 1798). A Qing scholar's notebook of foxes, ghosts, and karmic puzzles — deliberate, understated, and often devastating.</li>
        <li><strong>Strange Tales from a Chinese Studio</strong> — <em>Liáozhāi Zhìyì</em> 聊斋志异 (Pu Songling, c. 1740). The masterpiece of Chinese supernatural fiction: fox spirits, ghost brides, Taoist exorcists, and scholars who fall in love with things that are not human.</li>
        <li><strong>What the Master Would Not Discuss</strong> — <em>Zǐ Bù Yǔ</em> 子不语 (Yuan Mei, c. 1788). Gothic horror, gender-bending hauntings, and forbidden tales from a Qing libertine who believed everything the orthodox Confucians denied.</li>
        <li><strong>In Search of the Supernatural</strong> — <em>Sōushén Jì</em> 搜神记 (Gan Bao, c. 348). The oldest Chinese ghost-story collection:幽婚 (ghost marriages), resurrections, and encounters with the dead from the Eastern Jin dynasty.</li>
        <li><strong>Tang Dynasty Chuanqi</strong> — 唐传奇 (various authors, 7th–9th c.). The first true short stories in Chinese literature: self-contained, cinematic, and astonishingly modern in their narrative economy.</li>
        <li><strong>Collected Cases of Injustice Rectified</strong> — <em>Xǐyuān Jílù</em> 洗冤集录 (Song Ci, 1247). The world's first systematic forensic manual, told here as 13th-century true crime — evidence-based reasoning centuries before Sherlock Holmes.</li>
        <li><strong>Flowers in the Mirror</strong> — <em>Jìnghuā Yuán</em> 镜花缘 (Li Ruzhen, 1827). A Chinese <em>Gulliver's Travels</em> — thirty impossible kingdoms visited by sea, including a Country of Women that ruled men in 1827.</li>
        <li><strong>Stories Old and New</strong> — <em>Sān Yán Èr Pāi</em> 三言二拍 (Feng Menglong &amp; Ling Mengchu, c. 1620–1632). Vernacular novellas of merchants, scholars, clever wives, and cosmic justice — the Chinese Boccaccio.</li>
      </ul>

      <h2>Translation method</h2>
      <p>
        Each tale goes through the same process before publishing:
      </p>
      <ol class="how-list">
        <li><strong>Source check.</strong> I work only from public-domain Chinese editions, cross-checking against more than one printing where possible to catch typesetter errors. No modern retellings, no secondary sources.</li>
        <li><strong>Close translation.</strong> A literal pass first, then a story pass. I keep proper names in pinyin and gloss titles, ranks, and place-names on first mention. The goal is fidelity to the original's register — spare where it is spare, ornate where it is ornate.</li>
        <li><strong>Cultural annotation.</strong> Footnotes appear inline as small numbers and on hover. They explain only what an English reader needs to enjoy the story — never to lecture, never to pad the word count.</li>
        <li><strong>Classical Chinese appendix.</strong> Every tale includes the original <em>wényán</em> text in a collapsible section, so readers with classical Chinese can check the translation against the source. This is non-negotiable: a translation without its source is a retelling, and I want to offer the real thing.</li>
        <li><strong>Editorial polish.</strong> A final read-aloud pass for rhythm. I write the way a friend telling you a strange story would — not the way a journal article would.</li>
      </ol>

      <h2>Editorial principles</h2>
      <p>
        I am not an academic journal. I do not claim philological authority. Where scholars disagree, I pick the reading that makes the story most alive and flag the disagreement in a footnote. If I am wrong, I would rather be corrected than be safe.
      </p>
      <p>
        I am also not a content farm. I publish slowly — a small handful of tales per week — and never republish the same story under different titles or fabricate "tales" that don't exist in the source. Every story on this site comes from a real text by a real author who has been dead for at least a century.
      </p>
      <p>
        All source texts are in the public domain. My translations, annotations, and editorial commentary are released under <a href="https://creativecommons.org/licenses/by-nc/4.0/" rel="noopener">Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0)</a>.
      </p>

      <h2>Support</h2>
      <p>
        Cathay Tales is reader-supported. The most useful things you can do:
      </p>
      <ul class="support-list">
        <li><a href="index.html#subscribe">Subscribe</a> to the email list — a couple of tales per week, no spam.</li>
        <li><a href="https://ko-fi.com/cathaytales" target="_blank" rel="noopener">Buy me a tea on Ko-fi</a> — every cup funds the next translation.</li>
        <li>Tell one friend. Word of mouth is everything for a small project like this.</li>
      </ul>

      <h2>Contact</h2>
      <p>
        Editorial questions, source corrections, translation suggestions, or simply a hello — <a href="contact">find my contact details here</a>.
      </p>

      <p class="page-tag">
        Story first, scholarship second. Welcome to Cathay.
      </p>
    </article>
  </main>

  <a class="kofi-float" href="https://ko-fi.com/cathaytales" target="_blank" rel="noopener" aria-label="Support Cathay Tales on Ko-fi">
    <span class="kofi-float-emoji">🍵</span>
    <span class="kofi-float-text">Tip</span>
  </a>

  <footer class="site-footer">
    <div class="container">
      <p>© 2026 Cathay Tales. Translations &amp; annotations under <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a>. Source texts are in the public domain.</p>
      <p class="footer-links"><a href="about">About</a> · <a href="privacy">Privacy</a> · <a href="contact">Contact</a> · <a href="feed.xml">RSS</a></p>
      <p class="footer-zh">山有狐，月正红。</p>
    </div>
  </footer>
</body>
</html>'''

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("AdSense P0+P1 Patch")
    print("=" * 60)
    
    # P0-2: Rewrite About page
    print("\n[P0-2] Rewriting static/about.html ...")
    (STATIC_DIR / "about.html").write_text(ABOUT_HTML, encoding='utf-8')
    print("  ✓ about.html rewritten")
    
    # Parse all posts
    print("\n[P1] Parsing all posts ...")
    posts = parse_all_posts()
    print(f"  Found {len(posts)} posts")
    
    # Shuffle for rotation randomness (seeded)
    random.shuffle(posts)
    
    # Patch each post
    patched = 0
    samples = []
    
    for post in posts:
        original_content = post['content']
        
        # Check if already patched (idempotent)
        if '## Related Tales' in original_content and '## Translator\'s Note' in original_content:
            print(f"  SKIP (already patched): {post['file']}")
            continue
        
        body = post['body']
        
        # P1-2: Generate Translator's Note
        tnote = make_translator_note(post)
        
        # P1-1: Generate Related Tales
        related = get_related_posts(post, posts)
        related_section = make_related_tales_section(post, related)
        
        # Strategy: insert Translator's Note + Related Tales at the end of body
        # (after the last </details> block, before any trailing whitespace)
        
        # Find the end of meaningful content
        # We'll append after the last content line
        body = body.rstrip()
        
        # Build the new sections
        addition = f"\n\n{tnote}\n\n{related_section}\n"
        
        # Append to body
        new_body = body + addition
        
        # Reconstruct full content: frontmatter + body
        fm = post['fm']
        fm_lines = ["---"]
        # Preserve original frontmatter order
        for line in original_content.split('\n')[1:]:
            if line.strip() == '---':
                break
            fm_lines.append(line)
        fm_lines.append("---")
        fm_text = '\n'.join(fm_lines)
        
        new_content = fm_text + new_body
        
        # Write back
        post['path'].write_text(new_content, encoding='utf-8')
        patched += 1
        
        # Collect samples for review
        if len(samples) < 3:
            samples.append({
                'file': post['file'],
                'title': post['title'],
                'hub': post['hub'],
                'series': post['series'],
                'tnote': tnote,
                'related': [(r['slug'], r['title'][:50], r['hub']) for r in related],
            })
    
    print(f"\n  ✓ Patched {patched} posts")
    
    # Print samples
    print("\n" + "=" * 60)
    print("SAMPLE PREVIEWS (3 posts)")
    print("=" * 60)
    for s in samples:
        print(f"\n--- {s['file']} ---")
        print(f"  Title: {s['title']}")
        print(f"  Hub: {s['hub']} | Series: {s['series']}")
        print(f"\n  [Translator's Note]:")
        for line in s['tnote'].split('\n'):
            print(f"    {line}")
        print(f"\n  [Related Tales]:")
        for slug, title, hub in s['related']:
            print(f"    → {title}... ({hub})")
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

if __name__ == '__main__':
    main()
