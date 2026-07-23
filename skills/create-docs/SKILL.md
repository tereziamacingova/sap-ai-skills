---
name: create-docs
description: >
  Generates a complete, screenshot-rich HTML documentation page for a specific web application
  by navigating it with Playwright and capturing screenshots of each major screen.
  Use this skill only when the user explicitly asks to document a specific tool or URL —
  for example: "generate documentation for https://...", "create a user guide for this app",
  or "document the features of [named tool]". Do not trigger on generic requests like
  "document this" without a clear URL or app name. Requires the Playwright MCP server.
  Produces a self-contained HTML file with embedded screenshots and feature walkthroughs.
---

Create a complete, screenshot-rich HTML documentation page for any web application by autonomously navigating it with Playwright.

## Usage
`/create-docs <URL>`

If no URL is provided, ask for one.

---

## Steps

1. **Navigate and explore** — visit the URL, take a screenshot, then navigate through the main sections and features visible in the UI. Focus on publicly accessible content. Do not attempt to interact with controls that could trigger destructive actions, submit forms with real data, or access authenticated/private areas beyond what the user has explicitly authorised.

2. **Capture screenshots** at each meaningful state:
   - Landing / home screen
   - Each major section or tab
   - Key features and interactions
   - Any dialogs, panels, or expanded views worth documenting
   Save each screenshot with a descriptive filename to `~/Desktop/Claude/Docs/<tool-name>/screenshots/`

3. **Understand the tool** from what you see:
   - What does it do and who is it for?
   - How do you access it (URL, auth, prerequisites)?
   - What are the main features and how do they work?
   - Are there useful links, related tools, or resources visible?

4. **Write a complete standalone HTML documentation page** using the design system below.

5. **Save the output** to `~/Desktop/Claude/Docs/<tool-name>/<tool-name>-docs.html`

6. **Report back**: confirm what screens were captured, what features were documented, and the output file path.

---

## Design System

Use this CSS for all documentation pages — clean, professional, green-accented light theme.

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { margin:0; padding:0; box-sizing:border-box; }

:root {
  --green:#7a9e87; --green-light:#d4e8da; --green-pale:#f0f8f3;
  --text:#1a1a2e; --muted:#6b7280; --white:#ffffff; --border:#e2ece5;
  --shadow:0 4px 24px rgba(122,158,135,0.12);
}

body { font-family:"Inter",sans-serif; background:var(--green-pale); color:var(--text); line-height:1.65; }

.hero { background:linear-gradient(135deg,#2d5a3d 0%,var(--green) 50%,#a8c9b4 100%); color:#fff; padding:60px 64px 52px; }
.hero-badge { display:inline-block; background:rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.3); border-radius:20px; padding:4px 14px; font-size:10.5px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:16px; }
.hero h1 { font-size:38px; font-weight:700; margin-bottom:10px; }
.hero .tagline { font-size:15px; opacity:.9; max-width:620px; margin-bottom:26px; }
.hero-url { display:inline-flex; align-items:center; gap:10px; background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.22); border-radius:8px; padding:11px 18px; font-size:13px; }

.container { max-width:1080px; margin:0 auto; padding:0 36px; }
.content { padding:52px 0; display:flex; flex-direction:column; gap:48px; }

.sec-label { font-size:9.5px; font-weight:700; letter-spacing:2.5px; text-transform:uppercase; color:var(--green); margin-bottom:6px; }
.sec h2 { font-size:22px; font-weight:700; color:var(--text); margin-bottom:6px; }
.sec-desc { font-size:14px; color:var(--muted); margin-bottom:22px; }

.ss-card { background:var(--white); border:1px solid var(--border); border-radius:14px; overflow:hidden; box-shadow:var(--shadow); }
.ss-card img { width:100%; display:block; }
.ss-cap { padding:11px 18px; font-size:12px; color:var(--muted); background:var(--green-pale); border-top:1px solid var(--border); }

.two-col { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
.three-col { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }

.feature-card { background:var(--white); border:1px solid var(--border); border-radius:12px; padding:18px 20px; }
.feature-card .fc-icon { font-size:22px; margin-bottom:8px; }
.feature-card h3 { font-size:13px; font-weight:700; margin-bottom:4px; }
.feature-card p { font-size:11.5px; color:var(--muted); line-height:1.55; }

.info-box { background:var(--green-pale); border-left:4px solid var(--green); border-radius:0 10px 10px 0; padding:13px 18px; font-size:13px; margin:16px 0; }

.footer { background:linear-gradient(135deg,#1a3a25,#2d5a3d); color:rgba(255,255,255,0.6); padding:28px 64px; font-size:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; }
.footer strong { color:#fff; }
```

---

## Rules

- Be fully autonomous — explore everything you can reach without login walls blocking you
- If authentication is required, document what you can see and note auth requirements
- Embed all screenshots as base64 directly in the HTML so the file is fully self-contained
- Keep the HTML clean and readable

## Regeneration mode

If invoked with `--regenerate` and a previous docs folder exists:
- Re-run the full browser session
- Compare new screenshots against previous ones
- Update only the sections where the UI changed
- Add a changelog section at the top noting what changed and when
