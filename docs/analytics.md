# Cloudflare Web Analytics

The owner chose Cloudflare Web Analytics on 26 October 2026 while retaining GitHub Pages hosting and Namecheap DNS. The Cloudflare account has a separate `flowloop.io` analytics site using manual JS snippet installation. No hosting migration, proxy, DNS/email change or Cloudflare API credential is needed.

## Publication and coverage

Repository variable `CLOUDFLARE_WEB_ANALYTICS_TOKEN` holds the **public site identifier** from the Cloudflare-generated snippet. It is embedded in served HTML and is not an API key, source-reader token or other secret. The deployment workflow passes it to `assemble-site.py --cloudflare-web-analytics-token`. An absent/empty variable leaves output without this beacon.

Assembly adds Cloudflare's `type="module"` beacon before the closing body tag in the portfolio homepage, original app homepage and each approved CaveOS HTML page, after private content has been removed. The current five tracked pages are `/`, `/flowloop-app/`, `/caveos/`, `/caveos/behind-the-scenes.html` and `/caveos/credits.html`. The private standalone CaveOS Site and source files are unchanged. Privacy-policy files, download redirects, compatibility aliases and the 404 page receive no added beacon. Existing legacy app analytics/consent code is preserved.

The manifest records the provider, public site token and tracked output paths alongside file hashes. Rebuilding the same committed sources, policy and analytics configuration is deterministic. The validator checks exactly one matching beacon on every tracked page and none on other HTML pages; invalid token syntax, duplicate beacons or a missing closing body fail assembly before publication.

## Viewing and verifying

In the [Cloudflare dashboard](https://dash.cloudflare.com/), open **Web Analytics → flowloop.io**. Allow a few minutes after deployment for data to appear. Inspect the live page source for one Cloudflare beacon and inspect browser network activity for the script and beacon request. A successful deployment proves snippet publication; actual collected visits must be checked separately in Cloudflare.

Web Analytics is client-side measurement. Ad blockers and browser/network conditions can prevent collection; it is not an exact count of every request and is not a replacement for server logs. See [Cloudflare setup](https://developers.cloudflare.com/web-analytics/get-started/) and [measurement limitations](https://developers.cloudflare.com/web-analytics/faq/).

To disable collection, delete/empty `CLOUDFLARE_WEB_ANALYTICS_TOKEN` and redeploy. This removes the beacon from newly served pages; it does not erase already collected data. Hostname changes and deletion of the analytics site are managed in Cloudflare. Do not change existing personal-website analytics while managing FlowLoop.
