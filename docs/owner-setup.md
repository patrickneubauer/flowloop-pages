# Owner setup before production cutover

The CaveOS 14-file public boundary is approved. Production domain transfer and source privacy remain separate decisions. The connected `flowloop` collaborator can push code/run workflows, but has no repository administration. Current audit found no credentials, environments or activation variables.

## Simplest supported setup: two owner-created fine-grained tokens

Sign in as **patrickneubauer**. Create tokens at [GitHub fine-grained token settings](https://github.com/settings/personal-access-tokens/new), with expiry/rotation recorded securely. These are the existing workflow's fallback; leave `SOURCE_APP_ID` and `DISPATCH_APP_ID` unset. The preferred GitHub App alternative is described in [infrastructure.md](infrastructure.md).

1. **Source reader:** resource owner `patrickneubauer`; select only `flowloop.io` and `caveOS`; repository Contents **read** (Metadata read is implicit). Create the `source-read` environment in [deployment repository environments](https://github.com/patrickneubauer/flowloop-pages/settings/environments), restrict deployments to `main`, and store the token there as secret `SOURCE_READ_TOKEN`.
2. **Rebuild requester:** select only `flowloop-pages`; repository Contents **write** (the minimum GitHub requires for repository_dispatch; no Administration or Workflows permission). Store it as `PAGES_DISPATCH_TOKEN` in both [FlowLoop source Actions secrets](https://github.com/patrickneubauer/flowloop.io/settings/secrets/actions) and [CaveOS Actions secrets](https://github.com/patrickneubauer/caveOS/settings/secrets/actions).
3. Protect public deployment `main` with owner CODEOWNERS review and passing tooling checks, without an App/direct-push bypass. CODEOWNERS alone does not enforce review. Create a `github-pages` environment restricted to `main`.
4. In [deployment repository Pages settings](https://github.com/patrickneubauer/flowloop-pages/settings/pages), select **GitHub Actions**. Leave its custom domain empty. Do not detach `flowloop.io` from the current publisher yet.
5. Keep `SOURCE_BUILD_ENABLED`, `PAGES_DEPLOY_ENABLED` and both source `FLOWLOOP_DISPATCH_ENABLED` variables absent/off. Credentials are sufficient for the separate [Validate prepared migration workflow](https://github.com/patrickneubauer/flowloop-pages/actions/workflows/verify-migration.yml), which can run on main without activation variables.

Do not paste token/private-key values into chat, commits or source files. Enter them directly in GitHub's secret UI; saved secrets cannot be read back. The requester token's unavoidable Contents write permission is a reason to enforce main review rules before enabling it.

## Credential-backed preflight

Once setup is complete, tell the migration coordinator. Run **Validate prepared migration** on deployment `main`. It reads FlowLoop's reviewed `codex/multi-project-website` branch and CaveOS main, requires the approved publication policy and clean revisions, assembles and validates, and logs the exact revisions. It uploads/deploys nothing, so the current main/root production site stays intact.

Only after that succeeds should the coordinator ask for the production domain-transfer approval. The FlowLoop source PR must stay unmerged until the coordinated cutover. Making that source private waits for healthy replacement production and separate approval. The candidate-only preflight can be removed after cutover; the normal publisher continues reading both mains.
