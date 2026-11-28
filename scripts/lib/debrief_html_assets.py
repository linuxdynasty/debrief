#!/usr/bin/env python3
"""Offline CSS and vanilla JS assets for the /debrief v2 interactive HTML report."""

from debrief_fonts import FONT_FACE_CSS  # noqa: E402

REPORT_CSS = FONT_FACE_CSS + """
:root {
  color-scheme: light;
  --page: #F4F4F0;
  --surface: #FFFFFF;
  --subtle: #EAEEEB;
  --ink: #12212A;
  --muted: #50636A;
  --line: #CDD7D5;
  --track: #E4E9E7;
  --row-hover: #E4EBE7;
  --evidence: #0F7C72;
  --evidence-ink: #0A5F59;
  --evidence-soft: #DDF0EC;
  --adverse: #B23A3A;
  --adverse-ink: #962C2C;
  --adverse-soft: #F8E7E6;
  --direction: #5B48C8;
  --direction-soft: #ECE8FB;
  --briefing-ink: #2A2350;

  --s1: 4px;
  --s2: 8px;
  --s3: 12px;
  --s4: 20px;
  --s5: 32px;
  --s6: 48px;
  --s7: 72px;

  --fs-0: clamp(34px, 4.4vw, 58px);
  --fs-1: clamp(26px, 2.9vw, 34px);
  --fs-2: clamp(22px, 2.3vw, 26px);
  --fs-3: clamp(19px, 1.9vw, 21px);
  --fs-4: 18px;
  --fs-5: 16px;
  --fs-6: 13px;

  --radius: 2px;
  --radius-sm: 2px;
  --measure: 66ch;
  --font-sans: "Archivo", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: "Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0C1417;
    --surface: #131E22;
    --subtle: #172529;
    --ink: #E6F1F0;
    --muted: #93A9AB;
    --line: #26373B;
    --track: #1E2E32;
    --row-hover: #18292E;
    --evidence: #5FE3D0;
    --evidence-ink: #7DEFE0;
    --evidence-soft: #12312F;
    --adverse: #FF7B7B;
    --adverse-ink: #FF9C9C;
    --adverse-soft: #321F20;
    --direction: #B49CFF;
    --direction-soft: #211C3A;
    --briefing-ink: #E4DCFF;
  }
}

:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0C1417;
  --surface: #131E22;
  --subtle: #172529;
  --ink: #E6F1F0;
  --muted: #93A9AB;
  --line: #26373B;
  --track: #1E2E32;
  --row-hover: #16262A;
  --evidence: #5FE3D0;
  --evidence-ink: #7DEFE0;
  --evidence-soft: #12312F;
  --adverse: #FF7B7B;
  --adverse-ink: #FF9C9C;
  --adverse-soft: #321F20;
  --direction: #B49CFF;
  --direction-soft: #211C3A;
  --briefing-ink: #E4DCFF;
}

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
/* Start from zero, then give content primitives deliberate spacing. */
p { margin-bottom: var(--s3); }
p:last-child { margin-bottom: 0; }
ul, ol { padding-inline-start: var(--s4); }
select {
  max-width: 100%;
  padding: 4px 8px;
  background: none;
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.04em;
}
html {
  background: var(--page);
  overflow-x: clip;
  /* Disclosure must not move the page when a scrollbar appears. */
  scrollbar-gutter: stable;
}
body {
  counter-reset: section;
  margin: 0;
  padding: 0 24px var(--s7);
  background: var(--page);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: var(--fs-5);
  line-height: 1.55;
  font-kerning: normal;
  -webkit-font-smoothing: antialiased;
}
.grain {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  contain: strict;
  opacity: 0.04;
  pointer-events: none;
  z-index: 0;
}
body > .container { position: relative; z-index: 1; }
.container { max-width: 1180px; margin: 0 auto; }
p { margin: 0 0 var(--s4); max-width: var(--measure); }
a {
  color: var(--evidence-ink);
  text-decoration: none;
  border-bottom: 1px solid var(--line);
  padding-bottom: 1px;
}
a:hover { color: var(--ink); border-bottom-color: var(--ink); }
:focus-visible { outline: 2px solid var(--evidence-ink); outline-offset: 3px; }
strong { font-weight: 600; }
code {
  font-family: var(--font-mono);
  font-size: 0.92em;
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 1px 5px;
}
h1, h2, h3, h4 {
  color: var(--ink);
  margin: 0;
  line-height: 1.15;
  letter-spacing: -0.02em;
  font-weight: 550;
}
h1 { font-size: var(--fs-1); font-weight: 500; letter-spacing: -0.035em; }
h2 {
  position: relative;
  counter-increment: section;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--s3);
  font-size: var(--fs-1);
  font-weight: 500;
  letter-spacing: -0.03em;
  margin: var(--s7) 0 var(--s5);
  padding-top: var(--s3);
  border-top: 1px solid var(--ink);
  scroll-margin-top: var(--s5);
}
h2::before {
  content: counter(section, decimal-leading-zero);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  font-weight: 400;
  letter-spacing: 0.14em;
  color: var(--direction);
}
h2::after { content: none; }
h2:target::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  background: linear-gradient(90deg, var(--direction), transparent 72%);
  transform-origin: left center;
  animation: rule-settle 120ms ease-out both;
}
@keyframes rule-settle {
  from { transform: scaleX(0.2); opacity: 0.2; }
  to { transform: scaleX(1); opacity: 1; }
}
h3 { font-size: var(--fs-3); font-weight: 550; margin-bottom: var(--s3); }
h4 { font-size: var(--fs-4); font-weight: 600; margin: var(--s4) 0 var(--s2); }

.masthead {
  position: relative;
  padding: var(--s6) 0 var(--s5);
  border-bottom: 1px solid var(--line);
}
.masthead-top {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s3);
  margin-bottom: var(--s4);
}
.eyebrow {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  font-weight: 400;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--direction);
}
.masthead-rule { display: none; }
.masthead h1 { color: var(--ink); max-width: 30ch; }
.masthead .subtitle {
  margin: var(--s3) 0 0;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  line-height: 1.75;
  letter-spacing: 0.02em;
  max-width: 88ch;
}
.masthead-meta {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: var(--s3) var(--s4);
  margin: var(--s5) 0 0;
  padding-top: var(--s3);
  border-top: 1px solid var(--line);
}
.masthead-meta > div {
  display: flex;
  flex-direction: column-reverse;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
}
.masthead-meta dt {
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  line-height: 1.35;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}
.masthead-meta dd {
  margin: 0;
  font-size: var(--fs-2);
  font-weight: 500;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.masthead-meta .meta-sub { color: var(--muted); font-size: var(--fs-6); font-weight: 400; }

.theme-control { display: flex; align-items: center; gap: var(--s2); }
.theme-control .theme-label {
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}
.theme-toggle {
  padding: 3px 10px;
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  transition: border-color 80ms ease-in-out, color 80ms ease-in-out;
}
.theme-toggle:hover { border-color: var(--ink); color: var(--ink); }

.site-nav {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: var(--s2);
  margin: 0;
  padding: var(--s2) 0;
  background: var(--page);
  border-bottom: 1px solid var(--line);
}
.nav-links {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--s1);
  min-width: 0;
}
.site-nav a {
  display: inline-flex;
  align-items: center;
  gap: var(--s2);
  padding: 6px 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  transition: color 80ms ease-in-out, border-color 80ms ease-in-out, background-color 80ms ease-in-out;
}
.site-nav a::before {
  content: attr(data-index);
  color: var(--direction);
  font-size: 10px;
  letter-spacing: 0.1em;
}
.site-nav a:hover,
.site-nav a:focus-visible {
  color: var(--ink);
  border-color: var(--line);
  background: var(--subtle);
}
.site-nav a[aria-current="true"] {
  color: var(--ink);
  border-color: var(--ink);
}
.site-nav .nav-spacer { flex: 1 1 auto; }
.nav-action {
  padding: 6px 12px;
  background: none;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  transition: color 80ms ease-in-out, border-color 80ms ease-in-out;
}
.nav-action:hover { color: var(--ink); border-color: var(--ink); }

/* Group disclosure: one rule per group replaces ten section rules. */
.group {
  border-bottom: 1px solid var(--line);
  scroll-margin-top: 64px;
}
.group h2, .group [id^="section-"] { scroll-margin-top: 76px; }
.group > summary {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--s1) var(--s4);
  padding: var(--s6) 0;
  cursor: pointer;
  list-style: none;
}
.group > summary::-webkit-details-marker { display: none; }
.group > summary::after {
  content: "";
  order: 3;
  margin-left: auto;
  width: 8px;
  height: 8px;
  border-right: 1.5px solid var(--muted);
  border-bottom: 1.5px solid var(--muted);
  transform: rotate(45deg) translate(-2px, -2px);
  transition: transform 120ms ease-out, border-color 80ms ease-in-out;
}
.group > summary:hover::after { border-color: var(--ink); }
.group[open] > summary::after { transform: rotate(-135deg) translate(-2px, -2px); }
.group > summary:hover .group-title { color: var(--direction); }
.group-num {
  color: var(--direction);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.14em;
}
.group-title {
  color: var(--ink);
  font-size: var(--fs-2);
  font-weight: 500;
  letter-spacing: -0.02em;
  transition: color 80ms ease-in-out;
}
.group-hint {
  flex: 1 1 22ch;
  color: var(--muted);
  font-size: var(--fs-5);
}
.group-body { padding: var(--s2) 0 var(--s7); }
.group > .group-body > h2:first-child { margin-top: 0; }
.group .section-intro { margin-bottom: var(--s4); }
.group-body > :first-child { margin-top: 0; }

/* Sub-section heading inside a group: no rule, spacing carries the break. */
.group h2 {
  counter-increment: none;
  display: block;
  margin: var(--s7) 0 var(--s4);
  padding: 0;
  border-top: 0;
  font-size: var(--fs-3);
  font-weight: 500;
  letter-spacing: -0.02em;
}
.group h2::before { content: none; }

/* Method note: a native disclosure falls back to inline content without JS. */
details.note {
  position: relative;
  display: inline-block;
  margin: var(--s3) 0 var(--s4);
  vertical-align: top;
}
details.note > summary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  min-height: 32px;
  padding: 0;
  cursor: pointer;
  list-style: none;
  color: var(--direction);
  background: none;
  border: 1px solid var(--direction);
  border-radius: 50%;
  font-family: var(--font-sans);
  font-size: 0;
  font-weight: 600;
  line-height: 1;
  letter-spacing: normal;
  text-transform: none;
  transition: color 80ms ease-in-out, border-color 80ms ease-in-out, background-color 80ms ease-in-out;
}
/* The visible text remains the accessible name; only the info glyph is drawn. */
details.note > summary::before {
  content: "i";
  font-size: 15px;
  font-weight: 600;
  line-height: 1;
}
details.note > summary::after { content: none; }
details.note > summary::-webkit-details-marker { display: none; }
details.note > summary:hover,
details.note[open] > summary {
  color: var(--ink);
  background: var(--subtle);
  border-color: var(--ink);
}
details.note > summary:focus-visible {
  outline: 2px solid var(--direction);
  outline-offset: 3px;
}
details.note > p,
details.note > ul {
  margin: var(--s2) 0 0;
  color: var(--muted);
  font-family: var(--font-sans);
  font-size: var(--fs-5);
  font-weight: 400;
  line-height: 1.55;
  letter-spacing: normal;
  text-transform: none;
  max-width: 68ch;
}
/* Enhanced tooltip: fixed positioning escapes wide-table overflow containers. */
html[data-tooltips="true"] details.note > p,
html[data-tooltips="true"] details.note > ul {
  display: none;
  position: fixed;
  left: 20px;
  top: 20px;
  z-index: 60;
  width: min(360px, calc(100vw - 40px));
  max-height: 70vh;
  margin: 0;
  padding: var(--s3) var(--s4);
  overflow: auto;
  visibility: hidden;
  background: var(--surface);
  color: var(--ink);
  border: 1px solid var(--line);
  border-left: 2px solid var(--direction);
  box-shadow: 0 12px 30px rgb(0 0 0 / 0.18);
}
html[data-tooltips="true"] details.note > ul { padding-inline-start: 36px; }
html[data-tooltips="true"] details.note[open] > p,
html[data-tooltips="true"] details.note[open] > ul,
html[data-tooltips="true"] details.note.tooltip-hover > p,
html[data-tooltips="true"] details.note.tooltip-hover > ul {
  display: block;
}
html[data-tooltips="true"] details.note[open],
html[data-tooltips="true"] details.note.tooltip-hover { z-index: 60; }

.briefing {
  padding: var(--s5) 0 0;
}
.briefing-note {
  margin: var(--s6) 0 0;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.briefing-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s2) var(--s4);
  margin-bottom: var(--s5);
}
.briefing-index,
.briefing-note {
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}
.briefing-label {
  display: block;
  margin-bottom: var(--s3);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--direction);
}
.briefing-statement {
  max-width: 30ch;
  margin: 0;
  font-size: var(--fs-0);
  font-weight: 500;
  letter-spacing: -0.035em;
  line-height: 1.03;
  color: var(--ink);
}
.briefing-items {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--s5) var(--s6);
  margin-top: var(--s7);
}
.briefing-lead .see-more { margin-top: var(--s4); }
.briefing-item p {
  margin: 0 0 var(--s3);
  max-width: 36ch;
  color: var(--ink);
  font-size: var(--fs-4);
  line-height: 1.55;
}
.see-more {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--direction);
  border-bottom: 1px solid var(--line);
}
.see-more:hover { color: var(--direction); border-bottom-color: var(--direction); }

.session-banner {
  margin: var(--s5) 0 0;
  padding: var(--s4);
  background: var(--evidence-soft);
  border: 1px solid var(--line);
  border-left: 3px solid var(--evidence);
  border-radius: var(--radius-sm);
}
.session-banner-body { color: var(--ink); line-height: 1.6; }

.stat-label {
  margin-top: var(--s1);
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  line-height: 1.4;
}

.section-intro {
  max-width: 60ch;
  color: var(--muted);
  font-size: var(--fs-4);
  margin-bottom: var(--s5);
}
.charts-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s6);
  margin: var(--s5) 0 var(--s6);
}
.chart-card {
  margin: 0 0 var(--s6);
  padding: 0;
  background: none;
  border: 0;
  border-radius: 0;
}
.chart-title-row { display: flex; align-items: center; justify-content: space-between; gap: var(--s2); }
.chart-foot {
  margin: var(--s3) 0 0;
  color: var(--muted);
  font-family: var(--font-sans);
  font-size: var(--fs-5);
  letter-spacing: normal;
  line-height: 1.6;
  max-width: 72ch;
}
.chart-title {
  margin: 0 0 var(--s4);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: var(--fs-4);
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.01em;
  text-transform: none;
}
tbody tr { transition: background-color 80ms ease-in-out; }
td.date, th.date { white-space: nowrap; }
.verdict {
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.08em;
}
/* data-state="hover" mirrors :hover so static captures can show the state. */
tbody tr:hover,
tbody tr[data-state="hover"] {
  background: var(--row-hover);
  box-shadow: inset 2px 0 0 var(--evidence);
}
/* Reserve the hover-edge space on every row so text never shifts or touches it. */
th:first-child, td:first-child { padding-left: var(--s3); }
.card-hint { color: var(--muted); font-size: var(--fs-4); margin: 0 0 var(--s3); }
td .card-hint, th .card-hint { margin: 0; font-size: var(--fs-5); }
.charts-row > .chart-card { margin-bottom: 0; }
.chart-card:last-child { margin-bottom: 0; }
.skill-table { font-size: var(--fs-5); }

.project-areas, .big-wins, .friction-categories, .features-section, .patterns-section, .horizon-section {
  display: flex;
  flex-direction: column;
  gap: var(--s4);
  margin-bottom: var(--s5);
}
.project-area { padding: 0; }
.narrative {
  max-width: 68ch;
  padding: 0;
  background: none;
  border: 0;
}
.area-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s2);
  margin-bottom: var(--s2);
}
.area-name { color: var(--ink); font-size: var(--fs-3); font-weight: 500; letter-spacing: -0.02em; }
.area-count { color: var(--muted); font-size: var(--fs-5); white-space: nowrap; }
.area-desc { color: var(--muted); font-size: var(--fs-5); line-height: 1.55; margin: 0; max-width: 66ch; }
.narrative p { color: var(--ink); font-size: var(--fs-4); line-height: 1.65; margin-bottom: var(--s4); }
.narrative p:last-of-type { margin-bottom: 0; }
.key-insight {
  margin-top: var(--s4);
  padding: 0 0 0 var(--s4);
  background: none;
  border-left: 2px solid var(--evidence);
  color: var(--ink);
  font-size: var(--fs-5);
  line-height: 1.55;
}
.big-win {
  padding: var(--s2) 0 var(--s2) var(--s4);
  background: none;
  border-left: 2px solid var(--evidence);
  border-radius: 0;
}
.big-win-title { color: var(--evidence-ink); font-size: var(--fs-3); font-weight: 500; letter-spacing: -0.02em; margin-bottom: var(--s2); }
.big-win-desc { color: var(--ink); font-size: var(--fs-5); line-height: 1.5; margin: 0; }
.friction-category {
  padding: var(--s2) 0 var(--s2) var(--s4);
  background: none;
  border-left: 2px solid var(--adverse);
  border-radius: 0;
}
.friction-title { color: var(--adverse-ink); font-size: var(--fs-3); font-weight: 500; letter-spacing: -0.02em; margin-bottom: var(--s2); }
.friction-desc { color: var(--ink); font-size: var(--fs-5); margin: 0 0 var(--s2); }
.friction-examples { margin: 0 0 var(--s3) var(--s4); color: var(--ink); font-size: var(--fs-5); }
.friction-examples li { margin-bottom: var(--s1); }
.friction-fix {
  padding: 0 0 0 var(--s3);
  background: none;
  border-left: 1px solid var(--evidence);
  border-radius: 0;
  color: var(--ink);
  font-size: var(--fs-5);
}
.friction-fix strong { color: var(--evidence-ink); }
.col-guide {
  margin-top: var(--s4);
  padding: var(--s3) 0 0;
  background: none;
  border: 0;
  border-top: 1px solid var(--line);
  border-radius: 0;
  color: var(--muted);
  font-size: var(--fs-5);
}
.col-guide summary {
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
}
.col-guide ul { margin: var(--s2) 0 0 var(--s4); line-height: 1.55; }
.col-guide li { margin-bottom: var(--s1); }

.action-pill {
  display: inline-block;
  padding: 0;
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.act-create { color: var(--evidence-ink); }
.act-modify { color: var(--direction); }
.act-remove { color: var(--adverse-ink); }

.coach-item {
  padding: 0 0 0 var(--s3);
  margin-bottom: var(--s4);
  background: none;
  border-left: 1px solid var(--line);
  border-radius: 0;
  font-size: var(--fs-5);
}
.coach-item:last-child { margin-bottom: 0; }
.coach-user { border-left-color: var(--evidence); }
.coach-agent { border-left-color: var(--direction); }
.coach-title { color: var(--ink); font-size: var(--fs-4); font-weight: 500; letter-spacing: -0.01em; margin-bottom: var(--s1); }
.coach-ev { color: var(--muted); font-size: var(--fs-5); margin-bottom: var(--s2); }
.coach-act { color: var(--ink); font-size: var(--fs-5); }

.rules-section {
  margin-bottom: var(--s5);
  padding: var(--s3) 0 0;
  background: none;
  border: 0;
  border-top: 1px solid var(--line);
  border-radius: 0;
}
.rules-actions { margin-bottom: var(--s3); padding-bottom: var(--s3); border-bottom: 1px solid var(--line); }
.copy-all-btn, .copy-btn {
  padding: 5px 12px;
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  transition: border-color 80ms ease-in-out, color 80ms ease-in-out;
}
.copy-all-btn { background: var(--evidence-soft); color: var(--evidence-ink); border-color: var(--evidence); }
.copy-all-btn:hover, .copy-btn:hover { background: var(--track); }
.copy-all-btn.copied { background: var(--evidence); color: var(--surface); }
.rule-item {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--s2);
  padding: var(--s3) 0;
  border-bottom: 1px solid var(--line);
}
.rule-item:last-child { border-bottom: none; }
.cmd-checkbox { width: var(--s4); height: var(--s4); margin-top: var(--s1); accent-color: var(--evidence); }
.cmd-code {
  flex: 1;
  min-width: 240px;
  display: block;
  padding: var(--s2) var(--s3);
  background: var(--subtle);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-5);
  white-space: pre-wrap;
  word-break: break-word;
}
.cmd-why { width: 100%; color: var(--muted); font-size: var(--fs-5); padding-left: 0; }

.feature-card, .pattern-card {
  padding: var(--s2) 0 var(--s2) var(--s4);
  background: none;
  border: 0;
  border-left: 2px solid var(--evidence);
  border-radius: 0;
}
.horizon-card {
  padding: var(--s2) 0 var(--s2) var(--s4);
  background: none;
  border: 0;
  border-left: 2px solid var(--direction);
  border-radius: 0;
}
.feature-title, .pattern-title, .horizon-title {
  color: var(--ink);
  font-size: var(--fs-3);
  font-weight: 500;
  letter-spacing: -0.02em;
  margin-bottom: var(--s2);
}
.feature-oneliner, .pattern-summary { color: var(--ink); font-size: var(--fs-5); margin-bottom: var(--s2); }
.feature-why, .pattern-detail, .horizon-possible { color: var(--muted); font-size: var(--fs-5); line-height: 1.5; margin-bottom: var(--s2); }
.horizon-possible { color: var(--briefing-ink); }
.horizon-tip {
  margin-bottom: var(--s3);
  padding: 0 0 0 var(--s3);
  background: none;
  color: var(--ink);
  border-left: 1px solid var(--direction);
  border-radius: 0;
  font-size: var(--fs-5);
}
.copyable-prompt-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--s2);
  margin-top: var(--s2);
}
.copyable-prompt {
  flex: 1 1 320px;
  padding: var(--s3);
  background: var(--subtle);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-5);
  line-height: 1.5;
  white-space: pre-wrap;
}
.prompt-label {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-top: var(--s3);
}

.charts-row { margin-bottom: var(--s5); }
.bar-head {
  display: flex;
  justify-content: space-between;
  gap: var(--s2);
  padding-bottom: var(--s2);
  margin-bottom: var(--s2);
  border-bottom: 1px solid var(--ink);
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  font-weight: 400;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.bar-row { display: flex; align-items: center; gap: var(--s2); margin-bottom: var(--s2); }
.bar-label {
  width: 32%;
  flex-shrink: 0;
  color: var(--muted);
  font-size: var(--fs-5);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-track { flex: 1; height: var(--s2); background: var(--track); border-radius: var(--radius-sm); overflow: hidden; }
.bar-fill { height: 100%; border-radius: var(--radius-sm); background: var(--evidence); }
.bar-value {
  width: 84px;
  color: var(--ink);
  font-size: var(--fs-5);
  font-weight: 500;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.overlap-stats { display: flex; flex-wrap: wrap; gap: var(--s5); margin: var(--s3) 0; }
.overlap-num {
  color: var(--ink);
  font-size: var(--fs-2);
  font-weight: 500;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

table {
  width: 100%;
  margin-top: var(--s2);
  border-collapse: collapse;
  font-size: var(--fs-5);
}
th, td {
  padding: var(--s2) var(--s3) var(--s2) 0;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: baseline;
}
th {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  font-weight: 400;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: none;
  border-bottom: 1px solid var(--ink);
  vertical-align: bottom;
}
td code, th code { border: 0; padding: 0; font-size: 0.95em; background: none; white-space: nowrap; }
th:first-child, td:first-child { white-space: nowrap; }
td.num { white-space: nowrap; }
th.num { white-space: normal; }
.col-guide ul { max-width: 82ch; }
tbody tr:last-child td { border-bottom: none; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.table-scroll { overflow-x: auto; }

.delta-up { color: var(--evidence-ink); font-weight: 700; }
.delta-down { color: var(--adverse-ink); font-weight: 700; }
.delta-flat { color: var(--muted); }
.status-badge {
  display: inline-block;
  padding: 0;
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}
.status-good { color: var(--evidence-ink); }
.status-bad { color: var(--adverse-ink); }
.status-warn { color: var(--direction); }
.status-neutral { color: var(--muted); }

.caveats {
  margin-top: var(--s6);
  padding: 0 0 0 var(--s3);
  border-left: 2px solid var(--line);
  background: none;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  color: var(--muted);
  font-size: var(--fs-5);
}
.caveats strong { color: var(--ink); }
.caveats ul { margin: var(--s2) 0 0 var(--s4); }
.caveats li { margin-bottom: var(--s1); }

svg text { font-family: var(--font-sans); }
svg .plot-frame { fill: var(--surface); stroke: var(--line); }
svg .plot-grid { stroke: var(--track); }
svg .plot-axis { stroke: var(--muted); }
svg .plot-tick { fill: var(--muted); }
svg .plot-label { fill: var(--ink); }
svg .plot-muted { fill: var(--muted); }
svg .plot-ideal { fill: var(--evidence-ink); }
svg .series-current-line { stroke: var(--evidence); }
svg .series-current-area { fill: var(--evidence-soft); stroke: var(--evidence); }
svg .series-prev-line { stroke: var(--muted); }
svg .series-prev-area { fill: var(--subtle); stroke: var(--muted); }
svg .dot-current { fill: var(--evidence); stroke: var(--surface); }
svg .dot-frontier { fill: var(--evidence); }
svg .dot-knee { fill: var(--direction); }
svg .dot-dominated { fill: var(--adverse); }
svg .dot-ring { stroke: var(--surface); }
svg .is-front { fill: var(--evidence-ink); }
svg .is-knee { fill: var(--direction); }
svg .is-dominated { fill: var(--muted); }
.legend-key.is-front { color: var(--evidence-ink); }
.legend-key.is-knee { color: var(--direction); }
.legend-key.is-dominated { color: var(--muted); }
.legend-swatch {
  display: inline-block;
  width: var(--s3);
  height: 2px;
  margin-right: var(--s1);
  background: var(--evidence);
  vertical-align: middle;
}
.legend-dash { height: 0; background: none; border-top: 2px dashed var(--muted); }
.mono { font-family: var(--font-mono); }

.radar-split { display: flex; flex-wrap: wrap; gap: var(--s4); align-items: center; }
.radar-plot { flex: 0 1 520px; min-width: 0; }
.plot-scroll { overflow-x: auto; }
.radar-table { flex: 1 1 300px; min-width: 0; overflow-x: auto; }
.radar-table td, .radar-table th { white-space: nowrap; }

/* Metric deltas read as a definition row, not as six little cards. */
.pill-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0;
  margin-bottom: var(--s5);
  border-top: 1px solid var(--line);
}
.pill { padding: var(--s3) var(--s3) var(--s3) 0; }
.pill-label {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-6);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 2px;
}
.pill-value { font-size: var(--fs-5); font-weight: 500; font-variant-numeric: tabular-nums; }

.notice {
  margin-bottom: var(--s4);
  padding: 0 0 0 var(--s3);
  border: 0;
  border-left: 2px solid var(--line);
  border-radius: var(--radius-sm);
  font-size: var(--fs-5);
}
.notice ul { margin: var(--s2) 0 0 var(--s4); }
.notice li { margin-bottom: var(--s1); }
.notice-warn { background: var(--direction-soft); border-left-color: var(--direction); color: var(--briefing-ink); }
.notice-bad { background: var(--adverse-soft); border-left-color: var(--adverse); color: var(--adverse-ink); }

@media (max-width: 1000px) {
  .masthead-meta { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .briefing-items { grid-template-columns: minmax(0, 1fr); gap: var(--s5); }
  .briefing-statement { max-width: 34ch; }
}
@media (max-width: 680px) {
  body { padding: 0 var(--s4) var(--s6); }
  .masthead { padding: var(--s5) 0 var(--s4); }
  .briefing-head { gap: var(--s1) var(--s3); }
  .charts-row { grid-template-columns: minmax(0, 1fr); }
  /* Wide tables scroll inside their own card instead of widening the page. */
  .chart-card, .radar-table, .plot-scroll { overflow-x: auto; }
  .chart-card table { min-width: 0; }
  .bar-label { width: 124px; }
  .briefing-statement { max-width: none; font-size: clamp(26px, 7.4vw, 34px); }
  .masthead-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  /* One scrollable row keeps the pinned bar at 44px instead of three rows. */
  .site-nav { padding: var(--s1) 0; }
  .nav-links {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
  }
  .nav-links::-webkit-scrollbar { display: none; }
  .site-nav a { white-space: nowrap; padding: 6px 9px; }
  .nav-action { flex: 0 0 auto; white-space: nowrap; padding: 6px 9px; }
  .group > summary { padding: var(--s4) 0; }
  .group h2 { margin-top: var(--s6); }
  .group-body { padding-bottom: var(--s6); }
  .group-hint { display: none; }
  .group-title { font-size: var(--fs-3); }
  h2 { margin-top: var(--s6); }
  h2::before { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  h2:target::after { animation: none; }
}
@media print {
  body { background: #FFFFFF; }
  .theme-control, .site-nav, .nav-action { display: none; }
  .masthead { border-bottom: 1px solid var(--line); }
  .chart-card, .project-area, .narrative, .briefing, .masthead { break-inside: avoid; }
  .grain { display: none; }
  details.note > summary { display: none; }
  html[data-tooltips="true"] details.note > p,
  html[data-tooltips="true"] details.note > ul {
    display: block;
    position: static;
    width: auto;
    max-height: none;
    padding: var(--s2) 0 0;
    overflow: visible;
    visibility: visible;
    background: none;
    color: var(--muted);
    border: 0;
    box-shadow: none;
  }
}
"""

REPORT_JS = """
const THEME_KEY = 'debrief-theme';
function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === 'light' || mode === 'dark') {
    root.setAttribute('data-theme', mode);
  } else {
    root.removeAttribute('data-theme');
  }
  const btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.textContent = mode === 'light' ? 'Light' : (mode === 'dark' ? 'Dark' : 'Auto');
    btn.setAttribute('aria-label', 'Color theme: ' + (mode === 'light' ? 'light' : (mode === 'dark' ? 'dark' : 'follow system')));
  }
}
function cycleTheme() {
  let mode = 'auto';
  try { mode = localStorage.getItem(THEME_KEY) || 'auto'; } catch (e) { mode = 'auto'; }
  const next = mode === 'auto' ? 'light' : (mode === 'light' ? 'dark' : 'auto');
  try {
    if (next === 'auto') { localStorage.removeItem(THEME_KEY); } else { localStorage.setItem(THEME_KEY, next); }
  } catch (e) {}
  applyTheme(next);
}
function copyText(btn) {
  const code = btn.previousElementSibling;
  if (!code || !navigator.clipboard) return;
  navigator.clipboard.writeText(code.textContent).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy'; }, 1800);
  });
}
function copyRuleItem(idx) {
  const cb = document.getElementById('rule-' + idx);
  if (!cb || !navigator.clipboard) return;
  navigator.clipboard.writeText(cb.dataset.text || '').then(() => {
    const btn = cb.parentElement.querySelector('.copy-btn');
    if (btn) { btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = 'Copy'; }, 1800); }
  });
}
function copyAllCheckedRules() {
  const cbs = document.querySelectorAll('.cmd-checkbox:checked');
  const texts = [];
  cbs.forEach(cb => { if (cb.dataset.text) texts.push(cb.dataset.text); });
  if (!texts.length || !navigator.clipboard) return;
  navigator.clipboard.writeText(texts.join('\\n\\n')).then(() => {
    const btn = document.querySelector('.copy-all-btn');
    if (btn) {
      btn.textContent = 'Copied ' + texts.length + ' items!';
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = 'Copy All Checked'; btn.classList.remove('copied'); }, 1800);
    }
  });
}
function updateHourHistogram(offsetHours) {
  const periods = [
    { label: 'Morning (6-12)', range: [6,7,8,9,10,11] },
    { label: 'Afternoon (12-18)', range: [12,13,14,15,16,17] },
    { label: 'Evening (18-24)', range: [18,19,20,21,22,23] },
    { label: 'Night (0-6)', range: [0,1,2,3,4,5] }
  ];
  const adj = {};
  for (const [hr, cnt] of Object.entries(rawUtcHours)) {
    const nh = (parseInt(hr, 10) + offsetHours + 24) % 24;
    adj[nh] = (adj[nh] || 0) + cnt;
  }
  const rows = periods.map(p => ({ label: p.label, count: p.range.reduce((s, h) => s + (adj[h] || 0), 0) }));
  const maxC = Math.max(...rows.map(r => r.count), 1);
  const el = document.getElementById('hour-histogram');
  if (!el) return;
  el.textContent = '';
  rows.forEach(r => {
    const row = document.createElement('div'); row.className = 'bar-row';
    const lbl = document.createElement('div'); lbl.className = 'bar-label'; lbl.textContent = r.label;
    const trk = document.createElement('div'); trk.className = 'bar-track';
    const fil = document.createElement('div'); fil.className = 'bar-fill';
    fil.style.width = ((r.count / maxC) * 100) + '%';
    trk.appendChild(fil);
    const val = document.createElement('div'); val.className = 'bar-value'; val.textContent = r.count;
    row.appendChild(lbl); row.appendChild(trk); row.appendChild(val);
    el.appendChild(row);
  });
}
function groupDetails() {
  return Array.prototype.slice.call(document.querySelectorAll('details.group'));
}
function syncExpandLabel() {
  const btn = document.getElementById('expand-toggle');
  if (!btn) return;
  const groups = groupDetails();
  const allOpen = groups.length > 0 && groups.every(g => g.open);
  btn.textContent = allOpen ? 'Collapse all' : 'Expand all';
  btn.setAttribute('aria-expanded', allOpen ? 'true' : 'false');
}
function toggleAllGroups() {
  const groups = groupDetails();
  const allOpen = groups.length > 0 && groups.every(g => g.open);
  groups.forEach(g => { g.open = !allOpen; });
  syncExpandLabel();
}
function revealHash() {
  const id = decodeURIComponent((location.hash || '').replace('#', ''));
  if (!id) return;
  const target = document.getElementById(id);
  if (!target) return;
  let node = target;
  while (node) {
    if (node.tagName === 'DETAILS') { node.open = true; }
    node = node.parentElement;
  }
  const group = target.closest('details.group');
  if (group) { setCurrentGroup(group.id); }
  syncExpandLabel();
}
function reportNavLinks() {
  return Array.prototype.slice.call(document.querySelectorAll('.site-nav a[href^="#"]'));
}
function setCurrentGroup(id) {
  reportNavLinks().forEach(a => {
    if (a.getAttribute('href') === '#' + id) { a.setAttribute('aria-current', 'true'); }
    else { a.removeAttribute('aria-current'); }
  });
}
function watchNoteTooltips() {
  const notes = Array.prototype.slice.call(document.querySelectorAll('details.note'));
  if (!notes.length) return;
  document.documentElement.setAttribute('data-tooltips', 'true');
  const contentFor = note => Array.prototype.find.call(note.children, el => el.tagName === 'P' || el.tagName === 'UL');
  const position = note => {
    const content = contentFor(note);
    const summary = note.querySelector('summary');
    if (!content || !summary) return;
    requestAnimationFrame(() => {
      if (!note.open && !note.classList.contains('tooltip-hover')) return;
      const rect = summary.getBoundingClientRect();
      const width = Math.min(360, window.innerWidth - 40);
      content.style.width = width + 'px';
      const height = content.offsetHeight;
      const left = Math.max(20, Math.min(rect.left, window.innerWidth - width - 20));
      let top = rect.bottom + 8;
      if (top + height > window.innerHeight - 20) { top = Math.max(20, rect.top - height - 8); }
      content.style.left = Math.round(left) + 'px';
      content.style.top = Math.round(top) + 'px';
      content.style.visibility = 'visible';
    });
  };
  notes.forEach((note, index) => {
    const summary = note.querySelector('summary');
    const content = contentFor(note);
    if (summary && content) {
      if (!content.id) { content.id = 'method-note-' + (index + 1); }
      content.setAttribute('role', 'tooltip');
      summary.setAttribute('aria-describedby', content.id);
      if (!summary.getAttribute('aria-label')) { summary.setAttribute('aria-label', summary.textContent.trim() || 'How to read'); }
    }
    note.addEventListener('pointerenter', () => {
      note.classList.remove('tooltip-dismissed');
      note.classList.add('tooltip-hover');
      position(note);
    });
    note.addEventListener('pointerleave', () => {
      note.classList.remove('tooltip-hover', 'tooltip-dismissed');
    });
    if (summary) { summary.addEventListener('click', () => position(note)); }
  });
  document.addEventListener('click', event => {
    notes.forEach(note => { if (note.open && !note.contains(event.target)) { note.open = false; } });
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    notes.forEach(note => {
      note.open = false;
      note.classList.remove('tooltip-hover');
      note.classList.add('tooltip-dismissed');
    });
  });
  window.addEventListener('scroll', () => {
    notes.forEach(note => { note.open = false; note.classList.remove('tooltip-hover'); });
  }, { passive: true });
  window.addEventListener('resize', () => { notes.filter(n => n.open).forEach(position); });
}
function watchGroups() {
  const links = reportNavLinks();
  const groups = groupDetails();
  if (!groups.length) return;
  const updateFromScroll = () => {
    const nav = document.querySelector('.site-nav');
    const readingLine = (nav ? nav.getBoundingClientRect().height : 0) + 32;
    let current = groups[0];
    groups.forEach(g => {
      if (g.getBoundingClientRect().top <= readingLine) { current = g; }
    });
    setCurrentGroup(current.id);
  };
  let scheduled = false;
  const scheduleUpdate = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled = false; updateFromScroll(); });
  };
  links.forEach(a => a.addEventListener('click', () => {
    setCurrentGroup(a.getAttribute('href').slice(1));
    requestAnimationFrame(updateFromScroll);
  }));
  groups.forEach(g => {
    const summary = g.querySelector('summary');
    if (summary) {
      summary.addEventListener('click', () => {
        if (!g.open) { setCurrentGroup(g.id); }
        requestAnimationFrame(updateFromScroll);
      });
    }
  });
  window.addEventListener('scroll', scheduleUpdate, { passive: true });
  window.addEventListener('resize', scheduleUpdate);
  updateFromScroll();
}
document.addEventListener('DOMContentLoaded', () => {
  let saved = 'auto';
  try { saved = localStorage.getItem(THEME_KEY) || 'auto'; } catch (e) { saved = 'auto'; }
  applyTheme(saved);
  const themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) { themeBtn.addEventListener('click', cycleTheme); }
  const sel = document.getElementById('timezone-select');
  if (sel) {
    sel.addEventListener('change', () => {
      const off = parseInt(sel.value, 10);
      updateHourHistogram(Number.isNaN(off) ? 0 : off);
    });
    const initOff = parseInt(sel.value, 10);
    updateHourHistogram(Number.isNaN(initOff) ? -5 : initOff);
  }
  syncExpandLabel();
  watchGroups();
  watchNoteTooltips();
  revealHash();
  const expandBtn = document.getElementById('expand-toggle');
  if (expandBtn) { expandBtn.addEventListener('click', toggleAllGroups); }
  groupDetails().forEach(g => g.addEventListener('toggle', syncExpandLabel));
  window.addEventListener('hashchange', revealHash);
  const printOpen = () => { groupDetails().forEach(g => { g.dataset.wasOpen = g.open ? '1' : '0'; g.open = true; }); };
  const printRestore = () => { groupDetails().forEach(g => { if (g.dataset.wasOpen === '0') { g.open = false; } }); };
  window.addEventListener('beforeprint', printOpen);
  window.addEventListener('afterprint', printRestore);
});
"""
