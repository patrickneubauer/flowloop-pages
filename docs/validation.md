# Migration validation — 25 October 2026

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

Cross-repository installation-token reads, source-main automatic dispatch, manual production redeploy, a successful Pages artifact/deployment, domain reassignment, live route/HTTPS verification after cutover, source privacy and rollback in production remain **pending**. No credential was provisioned or copied from local OAuth into CI. These are acceptance gates, not completed work.

The source publication profile is now owner-approved; activation variables remain off/absent. The existing production domain and repository visibility remain unchanged. Local tests cannot establish the missing live evidence. A failing synthetic build proves local refusal semantics; it is not a production-failure drill.

## Remote execution evidence

Bootstrap run `40207938001` failed in synthetic local-preview cases as described above. Deployment run `40207937882` was skipped because source/publication activation is absent. Corrected run [40208068685](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40208068685) passed all 13 tests at tooling revision `bda59d3637afaad95aa4fbb92805bd5c5c73ea0a`. Its deployment run `40208068683` was skipped as intended. No public-source assembly is enabled by these preparation commits.

Final local preview was regenerated from clean committed source trees: FlowLoop `bf5a0fc927bd217e8be5e68dddf5bff088c33f93`, CaveOS `42ef2a16d0d4a207c6c7531e9f6687b2c0b1f7a8`, tooling `bda59d3637afaad95aa4fbb92805bd5c5c73ea0a`. Its manifest has 322 hashed files, exactly 14 under CaveOS, all dirty flags false, and the local unapproved marker. The policy remains pending.

Source reviews: [FlowLoop draft PR 1](https://github.com/patrickneubauer/flowloop.io/pull/1), [CaveOS draft PR 1](https://github.com/patrickneubauer/caveOS/pull/1). GitHub mapped both source commits to `patrickneubauer` for author and committer. Production Pages/domain/visibility were rechecked unchanged after preparation push.


## Approval follow-up — 25 October 2026

The owner explicitly approved the proposed 14-file CaveOS profile, including the technical explainer’s minor mechanics disclosure. CaveOS PR 1 is merged at `a2afac81d55c41d2bf70690509452e60e29245e7`; GitHub attributes author/committer to patrickneubauer. Its new main-push notifier [run 40209692547](https://github.com/patrickneubauer/caveOS/actions/runs/40209692547) was skipped as intended because activation remains absent.

Normal assembly/validation ran with `CI=true GITHUB_ACTIONS=true`, no local bypass, using CaveOS approval commit `386d239c846d144f6ed55ae94550384960ca9501`, FlowLoop `bf5a0fc927bd217e8be5e68dddf5bff088c33f93` and tooling `ddbd608273b34c010fb34f203c81f7049eaf5e47`. It passed with 322 total files / 321 hashed files, no local review marker and exactly 14 CaveOS files. Every generated page/asset byte matched the reviewed preview; only revision metadata/local marker differed. Clean source flags were false for all dirty states. Planning validation passed again with 748 links. Browser checks were not repeated for an approval-metadata-only change.

Remote credential-backed validation remains pending: `flowloop` still has no admin permission and the deployment repository has no secrets, environments or variables. Added a manual `verify-migration.yml` preflight and owner checklist so the approved candidate can be checked with real credentials before altering production; no new activation or domain/visibility changes were made.
