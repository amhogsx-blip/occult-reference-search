# T.O.R.N. — Free Static Search (Option B)

This repo gives you a zero-cost search engine:
- A nightly crawler (GitHub Actions) collects titles/snippets/metadata from four sources
- Results are saved to `public/index.json`
- The retro 8-bit frontend (`public/index.html`) loads that JSON and searches locally with FlexSearch
- Host on GitHub Pages or Netlify for $0, then embed via <iframe> in Squarespace/Google Sites

## 1) Use this as your repo
- Create a new GitHub repo and upload these files (or drag the ZIP contents).
- Enable **GitHub Pages**: Settings → Pages → Deploy from branch → select the default branch, folder `/public`.

## 2) Allow the crawler to run
- GitHub → Actions tab → enable workflows (if prompted).
- The scheduled job runs nightly at 02:30 UTC, or you can click **Run workflow** to build now.

## 3) Point a subdomain (optional)
- Add a CNAME like `search.occultreference.net` to your GitHub Pages URL (or use Netlify if you prefer).
- Then embed on Squarespace/Google Sites:
  <iframe src="https://search.occultreference.net" style="width:100%;height:80vh;border:0"></iframe>

## 4) Customize
- Edit the list of sources in `crawler/crawler_rich.py` (SEEDS).
- Tweak the look in `public/index.html` (CSS).
- Limits: since this runs in the browser, keep the index modest (hundreds to a few thousand docs). If it grows too large, consider filtering to digitized items or trimming snippets.

## Notes
- The crawler is polite but basic. Always respect site terms; reduce crawl depth or frequency if asked.
- PDF text isn’t extracted in this free version; you can add it later with an offline step.
