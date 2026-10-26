# Production cutover and rollback

**Status: not authorized or performed.** The current site remains the production source. These steps require the repository owner/admin; the connected collaborator cannot change Pages settings or visibility. No DNS/email edits are expected.

## Preparation before asking for final cutover approval

1. Review and merge the three preparation branches/PRs. Merging the FlowLoop source changes its current branch-served site, so **do not merge that source PR while it is still the active legacy Pages publisher**. Use a separately tested prepared branch, and merge it during the approved cutover window after disabling/moving the old publisher.
2. Completed and verified on 26 October 2026: owner-created source-reader and requester secrets, main review protections, `source-read` and `github-pages` environments restricted to main, and Pages GitHub Actions source. The deployment custom domain is empty. All activation variables remain absent/off.
3. Completed on 25 October 2026: the owner approved the exact 14-file CaveOS boundary, including technical explanations and seven images. Approval is recorded in the private policy and the reviewed CaveOS change is on main. The standalone private Site is unaffected.
4. Completed on 26 October 2026: [Validate prepared migration run 40327860495](https://github.com/patrickneubauer/flowloop-pages/actions/runs/40327860495) passed against the reviewed FlowLoop branch and approved CaveOS main using the source-reader token; it uploaded/deployed nothing. A CaveOS manual requester smoke test reached the central workflow, which skipped with publication gates off. Normal publication continues to read main only. Automatic publication from both source-main pushes remains to be demonstrated after cutover; see [evidence and exact revisions](validation.md#credential-backed-checkpoint--26-october-2026).
5. Capture original Pages configuration and source SHA (`de7d4eee45d181e70e30c0a950563f3821fb27fd` at audit). Confirm a verified domain/HTTPS recovery route. Check owner-level custom-domain verification; any DNS TXT addition requires separate approval. Do not change nameservers or MX.

## Approved cutover window

Initial CaveOS public publication was approved on 25 October 2026. Obtain explicit approval for **domain transfer**, and later **FlowLoop source privacy**. Approval of one does not imply the others.

1. Record owner approval and chosen scope. Configure Pages on the public deployment repository with GitHub Actions, initially without the custom domain. Confirm its permissions/environment settings; no paid plan is needed.
2. Stop legacy branch publication / remove `flowloop.io` from the old repository's Pages assignment, without deleting the repository or history. Do not leave the same domain assigned to two Pages sites. GitHub UI/API behavior may require recreating the old Pages configuration on rollback.
3. Merge the reviewed FlowLoop source migration to main. Its root CNAME is source configuration only once old Pages publication is stopped. Verify author/committer metadata and resulting branch head.
4. Set central `SOURCE_BUILD_ENABLED=true`, both source `FLOWLOOP_DISPATCH_ENABLED=true`, then trigger a manual central build. Leave `PAGES_DEPLOY_ENABLED` off until the approved build/manifest has been checked.
5. Assign `flowloop.io` to `flowloop-pages`, confirm Actions as Pages source, enable `PAGES_DEPLOY_ENABLED=true` and run the deployment. DNS records should remain unchanged. GitHub may need time to reissue/attach its certificate; do not disable HTTPS as a shortcut.
6. Verify HTTPS apex/www redirects, portfolio root, `/flowloop-app/`, `/caveos/`, retained pages/assets, `/privacy.html`, `/download/` and representative old `/static/` resources. Check mobile and keyboard interactions against the generated output. Inspect live manifest revisions and artifact boundary.
7. Demonstrate one meaningful main commit from each source triggers a successful central publication; use needed documentation corrections rather than empty noise commits. Trigger a manual redeploy. Run a deliberate synthetic failing build/check separately and confirm no deploy job follows; do not sabotage production source to test failure handling.
8. After replacement production is confirmed healthy and privacy approval is explicit, make `flowloop.io` private. Recheck that `flowloop-pages` is public and is the only Pages publisher, CaveOS remains private and source reads still work. Changing visibility cannot retract previously public history/clones.

Do not claim these live checks from local tests. Mark acceptance complete only after measured remote evidence.

## Rollback

Before source privacy changes: disable central deployment, detach its domain, restore the old source main to the recorded pre-migration revision with a reviewed revert (preserve history), restore Pages `main` + `/`, reassign `flowloop.io`, and confirm HTTPS/routes. The old CNAME and files are in Git history. Coordinate the removal/reassignment to avoid a domain conflict.

After source privacy changes on GitHub Free: the old private repository cannot serve as the same free Pages fallback. Keep `flowloop-pages` as public publisher and revert/rebuild approved source/tooling to a known-good artifact instead. If returning the source repository to public would expose new private changes, it requires a separate explicit decision. Do not make it public automatically.

For routine rollback, review/revert the faulty source commit on its trusted main, let its notifier rebuild, and inspect the resulting manifest. If only tooling failed, revert that tooling change and manually redeploy. Current workflow always assembles both latest mains, so freeze concurrent source changes while recovering an exact earlier combination. Preserve the previous successful Pages deployment until validation passes.
