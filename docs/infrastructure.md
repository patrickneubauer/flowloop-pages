# FlowLoop infrastructure

## Ownership and current state

Baseline audit: **25 October 2026**; credential/settings checkpoint: **26 October 2026**. Domain registrar and authoritative DNS: Namecheap BasicDNS. Website hosting: GitHub Pages, with no paid hosting dependency. The connected account is `flowloop`, a write collaborator; the owner is `patrickneubauer`. Write access does not grant repository administration.

| Repository | Audited visibility | Responsibility / target |
| --- | --- | --- |
| `patrickneubauer/flowloop.io` | Public | Canonical portfolio and original app; private only after approved, verified cutover |
| `patrickneubauer/caveOS` | Private | Canonical game and `website/`; stays private |
| `patrickneubauer/flowloop-pages` | Public | Publication tooling and Pages artifact deployment |

At the baseline audit, the old source repository hosted Pages from `main` and `/`, with custom domain `flowloop.io`, HTTPS enforced and an approved certificate for apex and www (audited expiry 20 January 2027). Apex and `/privacy.html` returned HTTP 200. At the baseline audit, `flowloop-pages` was an empty existing repository with no Pages configuration and no Actions secrets. The owner has since configured the credentials/settings described in the activation checkpoint below. No remote repository was recreated. Existing checkouts were inspected before cloning. The coordination directory is not a new Git repository; an unrelated pre-existing ancestor repository was left untouched.

## Static site assembly

The source repository owns root portfolio HTML and assets, plus `flowloop-app/` with the original app website. The CaveOS repository owns `website/dist/`, its publication annotations and `website/publication-profile.json`. The private standalone CaveOS Site and its `.openai/hosting.json` are preserved; GitHub publication neither invokes Sites tools nor changes that audience.

The central Python assembler copies only the portfolio paths, migrated app and explicit CaveOS file allowlist. It never executes scripts from the private repositories. CaveOS `data-publication="private"` subtrees are removed from generated HTML, the JSON gallery is pruned to approved entries, and canonical/social URLs are adapted to `/caveos/`. The complete private source remains intact. No game engine, save, private story page, development record, `.openai` identity or Git metadata enters the output.

Routes use lowercase project directory names and trailing slashes: `/`, `/flowloop-app/`, `/caveos/`. Existing sibling CaveOS `.html` page names remain valid. Pages redirects directory paths without a slash to their slash form. Source-specific styling remains independent. Root `/privacy.html` serves the exact original policy bytes, preserving external and App Store policy references. Root `/download/` and `/static/` are generated compatibility copies of the app directories; root legacy icons remain available. These are derived deployment aliases, not independent editable sources. Existing root hash links cannot redirect server-side on Pages; the new homepage includes the app link, and app anchors continue under `/flowloop-app/#...`.

`deployment-manifest.json` records source and orchestrator Git revisions, publication profile and generated file hashes. Rebuilding the same revisions/profile is deterministic. Generated output is never committed. Rollback uses reviewed Git reverts of sources/tooling followed by rebuilding both trusted mains; arbitrary source refs from dispatch input are deliberately unsupported.

## CaveOS publication boundary

The **owner-approved on 25 October 2026** `episode-1-2-promo-v1` profile contains three pages: homepage, technical explainer and credits. It retains seven existing images (Work Bay, gameplay capture and five runtime characters), CSS, two scripts and favicon. Gallery browsing is limited to the Work Bay and gameplay capture. The technical page includes architecture details and a clearly labelled minor Episode 1 puzzle-mechanics example; that disclosure was included in the owner’s explicit approval.

The whole-story and episode-guide pages are excluded in full. Later episode sections, concept portraits, later development artwork and links to omitted guides are removed from output. Hidden disclosures are not access control. The local audit inventories all 35 original served files; 14 are approved for publication. Approval is recorded in the private policy (`status`, `approved_by`, `approved_at`) after the owner reviews the actual generated preview. Do not set these fields speculatively. Normal later main commits rebuild this public profile automatically; a new file remains excluded until added deliberately. A material boundary expansion needs owner approval. Contributors must mark private additions and review public-page edits: an allowlist cannot determine whether new prose is a spoiler.

The policy was initially `pending` and is now `approved` after the owner’s explicit go-ahead. The gate still refuses any pending profile before an output/artifact is created. A local-only preview switch is rejected in CI. No private output may be uploaded to public Actions artifacts, even as a preview. The public tooling's tests use synthetic content only.

## Authentication and trust

Preferred setup: two owner-managed GitHub Apps, installed only on the required repositories.

| Credential | Installation / access | Store |
| --- | --- | --- |
| Source reader | `flowloop.io`, `caveOS`: Contents read, implicit Metadata read | `SOURCE_APP_ID` variable, `SOURCE_APP_PRIVATE_KEY` secret in deployment repository `source-read` environment |
| Rebuild requester | `flowloop-pages`: Contents write, implicit Metadata read | `DISPATCH_APP_ID` variable and `DISPATCH_APP_PRIVATE_KEY` secret in each private source repository |

Tokens are minted per job with the official pinned GitHub App action and revoked at job end. The reader action limits the installation token to both source repositories and Contents read. Source checkouts disable persisted credentials. There is no secret in files or output. No credential is copied from this machine's OAuth login into CI.

Simpler fallback: owner-created fine-grained tokens, each scoped to those same selected repositories/permissions. Store `SOURCE_READ_TOKEN` in `source-read`, and `PAGES_DISPATCH_TOKEN` in the source repositories; leave App ID variables absent. A collaborator's fine-grained token may not cover repositories owned by another personal account, so provision these as the owner. Use expiry, reminders outside this pipeline and rotation; do not create a classic broad `repo` PAT for convenience. Never paste keys into chat or tracked files. Use GitHub Settings → Secrets and variables, or `gh secret set` with secret input on stdin. Expired credentials fail a rebuild; they do not replace a healthy site.

GitHub requires Contents write for `repository_dispatch`; this is broader than a dispatch-only permission. A leaked requester token can affect deployment-repository content. Protect `main` against direct pushes/bypasses and require owner review for `.github/`, `scripts/`, tests and policy changes. CODEOWNERS names the owner but is **not enforcement**. Configure public repository rules with required review/status checks and no App bypass. Restrict the `source-read` and `github-pages` environments to `main`. Confirm environment/rules features available under the owner's free plan; private-source rules can have plan limitations. Keep the set of trusted source-main writers small.

Only trusted main jobs can access source credentials. Pull-request tests do not use secrets or private source. There is no `pull_request_target`, untrusted code checkout, shell interpolation of event payloads, or dispatch-controlled ref selection. Actions dependencies are pinned to verified immutable official commits. Updating pins requires review.

## Triggers and reliability

Each source's `notify-flowloop-pages.yml` runs for every main push (no path filter) and manual requests, after `FLOWLOOP_DISPATCH_ENABLED=true`. It sends `source-updated` to the central repository. Payload revisions are informational and ignored. The central workflow checks out current main sources, assembles/validates, uploads exactly the generated `public-site/` directory beside the orchestration checkout, then deploys with supported Pages actions if enabled. Only the central workflow deploys; output does not trigger source commits.

Workflow-level concurrency serializes publication with `cancel-in-progress: false`; a newer run cannot complete ahead of an older running deployment. Pending events can coalesce; each eventual run reads the latest mains. This avoids lost final state and unnecessary stale builds but is not a promise of one separate deployment for every commit. The deployed site always reports the exact two revisions used. A failed assembly/validation never reaches deployment. Pages deployment failures must be inspected in Actions/Pages; the workflow does not delete the existing deployment.

Private repositories' small notification jobs consume private Actions minutes. Public central builds use public Actions hosting. This fits GitHub Free hosting; it does not imply unlimited private Actions minutes. Keep paid usage/budgets disabled unless explicitly authorized. Manual retry is available in the central Actions UI. `SOURCE_BUILD_ENABLED` and `PAGES_DEPLOY_ENABLED` are operator switches, absent by default, not security substitutes for policy validation and protected refs.

## Domain, HTTPS and email

Verified DNS, preserved unchanged:

```text
NS  dns1.registrar-servers.com / dns2.registrar-servers.com
A @ 185.199.108.153 / 185.199.109.153 / 185.199.110.153 / 185.199.111.153
CNAME www patrickneubauer.github.io
MX 10 eforward1.registrar-servers.com
MX 10 eforward2.registrar-servers.com
MX 10 eforward3.registrar-servers.com
MX 15 eforward4.registrar-servers.com
MX 20 eforward5.registrar-servers.com
```

The current public DNS no longer returns the historical DreamHost address. No nameserver/provider change is needed for a same-account Pages transfer. Inspect account-level Pages domain verification before cutover: ownership TXT verification can protect against takeover, but adding a TXT record is a DNS change and needs approval. Avoid concurrent conflicting domain assignments. Follow the [cutover procedure](cutover.md), with explicit owner approval.

`forklift@flowloop.io` uses Namecheap forwarding to Gmail; Gmail sends through its configured alias/SMTP and Google App Password. Those are user-supplied architecture facts, not independently verified Gmail settings. No Gmail, MX, forwarding, SMTP or credential changes are part of this migration. OpenClaw remains out of scope.

## Operations and troubleshooting

- No build runs: check source notification workflow and `FLOWLOOP_DISPATCH_ENABLED`; inspect central `SOURCE_BUILD_ENABLED` and current main workflows. The receiving workflow must exist on its default branch.
- HTTP 401/403/404: check App installation selection, Contents permission, secret/environment placement and expiry. Do not print token values. Dispatch requires Contents write on the receiver; private checkouts require source Contents read.
- Approval failure: review policy and preview; never bypass it in Actions. A new allowlisted file or private content classification needs review.
- Missing asset or route: run validator locally. Keep sibling links relative under `/caveos/`, and app resources under `/flowloop-app/`. Source root aliases are generated by assembly.
- Deployment denied: verify Pages uses GitHub Actions, environment branch policy, `pages: write`, `id-token: write` and deployment activation. Only the owner/admin can configure settings here.
- Domain/TLS issue: compare authoritative/recursive DNS and Pages domain assignment before changing records. Check certificate issuance/status and redirect behavior. Do not diagnose today's failures from the historical propagation incident.
- Suspected disclosure: disable `PAGES_DEPLOY_ENABLED`, restrict source credentials, restore a known-safe deployment, inspect exposed artifact contents and rotate affected credentials if applicable. Removing a file cannot retract prior downloads or caches.

## Adding another project

Keep its canonical source independent. Add a reviewed mount slug and project card to the portfolio, explicit source checkout/least-privilege read access and an allowlisted assembly adapter. Update validators, sitemap, compatibility decisions and tests. Add a main-push notifier to that source. Establish a public policy for private content before enabling it. Do not add an editable copy under this repository.

## References

- [GitHub Pages availability and publication](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
- [Repository dispatch permissions](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [Deployment concurrency and environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)
- [Official GitHub App token action](https://github.com/actions/create-github-app-token)
- [Verify a Pages custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages)
- [Fine-grained token limitations](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)


## Current activation checkpoint

CaveOS PR 1 is integrated on main with the approved boundary; its notifier remains skipped because activation is absent. Normal publication-mode assembly passed locally with CI flags enabled and the rendered output matched the reviewed preview. The original standalone private Site was not republished. The following preflight checkpoint predates the production cutover recorded below.

Owner setup is complete as of 26 October 2026: fine-grained token secrets are present in their intended locations, both environments allow only main, Pages uses GitHub Actions with no custom domain, and main ruleset `25879207` requires one approval, CODEOWNERS review, approval of the latest push and an up-to-date `test` check, with no bypass. All activation variables remain absent/off. See [owner setup](owner-setup.md) for credential rotation.

The manual [prepared migration run 40327860495](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40327860495) passed using the source-reader token and the same assembler/validator. It uploaded/deployed nothing. A [CaveOS requester smoke test](https://github.com/patrickneubauer/caveOS/actions/runs/40329332895) successfully dispatched to the central workflow, which [skipped as intended](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40329351990); the temporary notifier flag was deleted afterward. FlowLoop’s stored requester secret has not yet been exercised, and no actual Pages publication or source-main automatic rebuild has been demonstrated. See [validation evidence](validation.md). The temporary preflight accepts no arbitrary refs/event payloads and can be removed after cutover.

## Production checkpoint — 26 October 2026

The owner separately approved the domain transfer and portfolio publication. Legacy branch publication was stopped before the two reviewed FlowLoop commits were fast-forwarded to main, preserving their author/committer metadata and rename history. A build-only run passed, then the owner browser session removed the old Pages domain and assigned it to this repository. The existing certificate is approved for apex/www and HTTPS enforcement is enabled. The old source Pages site is unpublished; no source workflow deploys it. No DNS or email setting changed.

The [first production deployment](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40336006632) and subsequent automatic publications from [FlowLoop](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40336537092) and [CaveOS](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40336748438) passed. Central `SOURCE_BUILD_ENABLED` and `PAGES_DEPLOY_ENABLED`, plus each source `FLOWLOOP_DISPATCH_ENABLED`, are true. All 319 served content-file hashes matched the live manifest, public routes/redirects passed, and sampled excluded CaveOS paths returned 404. See [validation evidence](validation.md) for exact revisions, browser checks and limits.

`flowloop.io` remains public until the owner separately approves privacy after live acceptance. CaveOS stays private; this deployment repository stays public. A real production rollback/fault drill has not been performed; synthetic refusal tests pass.
