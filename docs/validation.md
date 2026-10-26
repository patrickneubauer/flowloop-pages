# Migration validation — 25–26 October 2026

## Observed preparation results

| Check | Actual result |
| --- | --- |
| Repository access / state | All three remotes readable/writable as collaborator; FlowLoop and CaveOS main clean at audit, existing worktrees enumerated; deployment remote empty |
| Production baseline | HTTPS root and privacy HTTP 200; source Pages main/root, domain flowloop.io, approved certificate, HTTPS enforced |
| DNS and email boundary | Namecheap NS, four Pages A records, www CNAME and five forwarding MX records match requested values; no changes made |
| Tooling tests | `python3 -m unittest discover -s tests -v`: 13 tests pass, including approval failure, CI bypass rejection, traversal/symlinks, source parent symlinks, dirty-source refusal, redaction, gallery filtering, retained anchor closure, deterministic output, asset/hash and fragment failures |
| Actual-source local assembly | `assemble-site.py` and `validate-site.py` with `--allow-unapproved-local`: pass; exactly 14 CaveOS files; unapproved marker present; pending profile unchanged |
| Refusal behavior | Ordinary pending assembly and CI local-preview bypass each exit 2 before creating output; no public artifact uploaded |
| Compatibility | Original app privacy policy byte-identical to pre-migration source; root generated alias byte-identical; download/static aliases validated against migrated sources |
| CaveOS standalone preservation | All five HTML page event/content streams equal after ignoring publication marker attrs; full gallery retains all 18 original entries; other 29 served files byte-identical to base |
| JS syntax | 14 actually loaded local scripts and four inline script blocks pass `node --check`; standalone CaveOS scripts checked too |
| Workflow YAML | Four workflow files parsed successfully using Ruby YAML; GitHub execution evidence is recorded separately below |
| CaveOS planning validator | Existing backend venv ran `scripts/validate-planning.py`: pass; 748 links, fixtures, character sheets and task records checked; this is planning validation, not gameplay evaluation |
| Responsive browser checks | Portfolio, app, CaveOS home, technical and credits checked at 1440, 768, 390 and 320px; final document width does not exceed viewport; no failed loaded images observed |
| CaveOS keyboard/interaction | Gallery opens, ArrowRight advances 1/2 to 2/2, image loads; Escape closes/restores focus; LOOK→TALK keyboard navigation works; build dialog opens and Escape restores focus |
| Technical walkthrough | All five cases exercised to their actual final step; Next disables correctly, including the one-step changed-ID case; no browser errors observed in retained technical page |

Browser checks used a loopback-only server and the supported in-app browser. Static validators inspect all local referenced assets; the browser image check excludes images not yet loaded because of native lazy loading. Screenshots and the unapproved preview remain local outside all three repositories and are not GitHub artifacts. The owner subsequently approved the exact proposed public content boundary on 25 October 2026; new or expanded public content remains review-gated.

## Failures found and corrected

- Early sanitizer review found dropped closing anchor tags and unwanted reserialization of the original app/privacy HTML. Fixed with retained-anchor tracking and byte copying of all non-CaveOS HTML; regression checks pass.
- Initial assembly interface confused the root portfolio page with its CSS asset directory. Root index is now selected and validated correctly.
- The old app demo video was fixed at 1027px, causing real phone/tablet overflow. A max-width rule fixes it; all four viewport checks pass afterward.
- Two historical carousel CSS files referenced an absent play-icon PNG. Added a small repository-native SVG and corrected those references.
- Repaired malformed legacy GTM noscript markup while retaining analytics/consent setup. The app still has two historical Analytics IDs; no claims about their current effectiveness or consent correctness are made.
- An attempted blanket JS parse discovered two unused legacy `gtag*.js` files are HTML snippets. They are preserved unchanged and are not loaded as scripts; the measured syntax pass covers actual script references and inline blocks.
- The technical walkthrough's final case has one step, so an initial fixed four-click harness hit a disabled control. The corrected browser check follows actual enabled steps; all five cases pass. These controls are explanatory and made no model/game calls.

- First GitHub synthetic check failed because local-preview test cases inherited the runner's CI environment; the production CI guard correctly rejected them. The test harness now isolates its simulated local environment, while explicit CI-rejection cases restore CI flags. A local rerun with both CI flags enabled passes. No production guard or workflow environment was weakened.

## Not demonstrated yet

An actual production rollback/fault drill remains **unperformed**. The owner separately approved making `flowloop.io` private; that change and post-change source reads/deployment succeeded in the privacy checkpoint below. GitHub App installation tokens are not configured; owner-created fine-grained tokens are the measured authentication mechanism. No local OAuth credential was copied into CI.

Both source-main automatic publications, manual production publication, Pages artifact/deployment, domain reassignment and live routes/HTTPS are now demonstrated in the production checkpoint below. Thirteen synthetic tests establish approval/validation refusal behavior; no production source was deliberately broken to test a failed rebuild.

## Remote execution evidence

Bootstrap run `40207938001` failed in synthetic local-preview cases as described above. Deployment run `40207937882` was skipped because source/publication activation is absent. Corrected run [40208068685](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40208068685) passed all 13 tests at tooling revision `bda59d3637afaad95aa4fbb92805bd5c5c73ea0a`. Its deployment run `40208068683` was skipped as intended. No public-source assembly is enabled by these preparation commits.

Final local preview was regenerated from clean committed source trees: FlowLoop `bf5a0fc927bd217e8be5e68dddf5bff088c33f93`, CaveOS `42ef2a16d0d4a207c6c7531e9f6687b2c0b1f7a8`, tooling `bda59d3637afaad95aa4fbb92805bd5c5c73ea0a`. Its manifest has 322 hashed files, exactly 14 under CaveOS, all dirty flags false, and the local unapproved marker. The policy remains pending.

Source reviews: [FlowLoop draft PR 1](https://github.com/patrickneubauer/flowloop.io/pull/1), [CaveOS draft PR 1](https://github.com/patrickneubauer/caveOS/pull/1). GitHub mapped both source commits to `patrickneubauer` for author and committer. Production Pages/domain/visibility were rechecked unchanged after preparation push.


## Approval follow-up — 25 October 2026

The owner explicitly approved the proposed 14-file CaveOS profile, including the technical explainer’s minor mechanics disclosure. CaveOS PR 1 is merged at `a2afac81d55c41d2bf70690509452e60e29245e7`; GitHub attributes author/committer to patrickneubauer. Its new main-push notifier [run 40209692547](https://github.com/patrickneubauer/caveOS/actions/runs/40209692547) was skipped as intended because activation remains absent.

Normal assembly/validation ran with `CI=true GITHUB_ACTIONS=true`, no local bypass, using CaveOS approval commit `386d239c846d144f6ed55ae94550384960ca9501`, FlowLoop `bf5a0fc927bd217e8be5e68dddf5bff088c33f93` and tooling `ddbd608273b34c010fb34f203c81f7049eaf5e47`. It passed with 322 total files / 321 hashed files, no local review marker and exactly 14 CaveOS files. Every generated page/asset byte matched the reviewed preview; only revision metadata/local marker differed. Clean source flags were false for all dirty states. Planning validation passed again with 748 links. Browser checks were not repeated for an approval-metadata-only change.

At this 25 October checkpoint, remote credential-backed validation remained pending: `flowloop` had no admin permission and the deployment repository had no secrets, environments or variables. This setup gap was resolved by the owner on 26 October, as recorded below. Added a manual `verify-migration.yml` preflight and owner checklist so the approved candidate can be checked with real credentials before altering production; no new activation or domain/visibility changes were made.

## Credential-backed checkpoint — 26 October 2026

The owner configured fine-grained tokens directly in GitHub. The `SOURCE_READ_TOKEN` environment secret exists in deployment `source-read`; `PAGES_DISPATCH_TOKEN` exists as a repository secret in both sources. Values were never read or printed. Both deployment environments restrict branches to main. Pages uses GitHub Actions with an empty custom domain. Active main ruleset `25879207` requires a PR, one approval, CODEOWNERS review, approval of the latest push and the up-to-date `test` check; its bypass list is empty and force pushes are blocked.

[Validate prepared migration run 40327860495](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40327860495) succeeded. Job `121592299336` ran from 13:14:00 to 13:14:13 UTC. All 13 synthetic tests, both token-backed source checkouts, approved assembly and route/asset/boundary validation passed. It used:

| Input | Exact revision |
| --- | --- |
| Deployment main | `801b67fca3b148bbcee32fc08ef268bcba7f9211` |
| Prepared FlowLoop branch | `bf5a0fc927bd217e8be5e68dddf5bff088c33f93` |
| Approved CaveOS main | `a2afac81d55c41d2bf70690509452e60e29245e7` |

The App-token step skipped because this setup uses the supported fine-grained-token fallback. No artifact was uploaded and no deployment was attempted.

For a bounded requester smoke test, CaveOS’s previously absent `FLOWLOOP_DISPATCH_ENABLED` variable was temporarily set to true and its notifier was manually dispatched on main. [Run 40329332895](https://github.com/patrickneubauer/caveOS/actions/runs/40329332895) succeeded using `PAGES_DISPATCH_TOKEN`. It caused the central [repository_dispatch run 40329351990](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40329351990), created at 13:17:50 UTC, to skip because central activation remained absent. The temporary CaveOS variable was deleted and absent variables were rechecked afterward. This proves the CaveOS requester credential and event delivery, not an automatic source-push rebuild or successful publication. FlowLoop’s copy of the requester secret remains unexercised.

Production domain assignment, DNS/email and repository visibility are unchanged. The FlowLoop migration PR remains unmerged. Central `SOURCE_BUILD_ENABLED`, `PAGES_DEPLOY_ENABLED` and both source notifier activation variables remain absent/off. Domain cutover still requires explicit owner approval; source privacy requires a later separate approval after live acceptance.

## Cutover authorization checkpoint — 26 October 2026

The owner explicitly approved transferring the production domain to `flowloop-pages` and publishing the prepared portfolio. Execution has not begun: the connected collaborator has `admin=false`; available browser sessions are signed out or use that collaborator. An owner-authenticated session is required. Rechecked source mains remain at FlowLoop `de7d4eee45d181e70e30c0a950563f3821fb27fd` and CaveOS `a2afac81d55c41d2bf70690509452e60e29245e7`; the prepared FlowLoop branch remains `bf5a0fc927bd217e8be5e68dddf5bff088c33f93`. The old Pages domain remains assigned, the migration PR remains unmerged and central activation variables remain absent. Source privacy is not authorized.

## Production cutover — 26 October 2026

After explicit owner approval, an owner-authenticated Codex browser session changed the old Pages source from legacy branch publishing to Actions before the FlowLoop migration was fast-forwarded to main. Its two original reviewed commits retain Patrick Neubauer as author/committer. The old domain assignment was retained during the replacement build to reduce disruption, then removed and assigned to `flowloop-pages`. HTTPS enforcement is enabled with an approved apex/www certificate expiring 20 January 2027. Once replacement checks passed, the old Pages site was unpublished. DNS/email and private standalone CaveOS hosting were untouched.

| Measured event | Evidence / result |
| --- | --- |
| Main-source build before domain move | [40335639956](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40335639956): successful build/validation/upload; deploy skipped |
| Manual redeployment of final source revisions | [40337030980](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40337030980): successful build and deploy |
| First production publication | [40336006632](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40336006632): successful build and deploy |
| FlowLoop main push | Source `71a612e1e0e804e34ff1bf7663d5b174aa9e3eac`; [notifier 40336515077](https://github.com/patrickneubauer/flowloop.io/actions/runs/40336515077) and [central publication 40336537092](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40336537092) both succeeded |
| CaveOS main push | Source `a92f2b3c2c542c07d50cbd528e8e3cdcca4a9fe0`; [notifier 40336730156](https://github.com/patrickneubauer/caveOS/actions/runs/40336730156) and [central publication 40336748438](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40336748438) both succeeded |

Both main-push checks used necessary publication-status documentation updates; no empty commits or game changes were introduced. The served manifest then recorded those two source revisions and orchestration `801b67fca3b148bbcee32fc08ef268bcba7f9211`, all dirty flags false, 321 hashed files and exactly 14 CaveOS files. Both source notifier flags and central build/deploy flags are enabled.

Live HTTPS verification compared all 319 served content files with their SHA256 manifest entries: zero mismatches. CNAME and .nojekyll deployment metadata were excluded from HTTP checks. Root, app, CaveOS home/technical/credits, root privacy and download routes returned 200. HTTP/apex/www and missing project trailing slashes redirected to HTTPS apex routes. Excluded CaveOS story/episode pages and Archive image returned 404. The first verification harness omitted URL encoding for legacy filenames containing spaces; correcting encoding yielded the pass without changing production.

The supported browser rendered the live root, app and CaveOS home at 390px with no horizontal document overflow or failed loaded images. CaveOS gallery advanced from 1/2 to 2/2, Escape closed it, TALK selected its panel and the build-info dialog opened/closed. Earlier full local technical/keyboard/responsive checks remain applicable because served website bytes match the approved artifact. Desktop/mobile screenshots stay local outside repositories.

The first production dispatch request returned GitHub HTTP 500 and created no run; a checked retry succeeded. No approval or security guard was bypassed. At this cutover checkpoint, source privacy and a real production rollback/fault drill remained unperformed. The privacy checkpoint below records the subsequent approved visibility change.

## Source privacy checkpoint — 26 October 2026

The owner explicitly approved making `patrickneubauer/flowloop.io` private after the production acceptance report. The owner-authenticated browser completed that visibility change, and authenticated repository metadata confirmed `flowloop.io` private, CaveOS private and `flowloop-pages` public. No credentials, DNS/email, domain assignment or CaveOS private Site settings were changed. Existing public history/clones are not retracted by this change.

[Post-privacy deployment 40339545186](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40339545186) passed all 13 tests, both private-source checkouts, approved assembly/validation, artifact upload and Pages deployment. This verifies the owner-created fine-grained reader still works when both source repositories are private; the GitHub App alternative remains unconfigured.

The required source README visibility update at `c976566f746d8844687c5c787430928fef716561` then triggered [private-source notifier 40339735007](https://github.com/patrickneubauer/flowloop.io/actions/runs/40339735007) and [automatic central publication 40339755127](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40339755127); both succeeded. The existing requester credential and enabled source-main trigger therefore also work after the source became private.
