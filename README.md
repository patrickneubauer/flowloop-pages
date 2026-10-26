# FlowLoop Pages

Public deployment orchestration for [FlowLoop.io](https://flowloop.io/). Editable websites live in `patrickneubauer/flowloop.io` and `patrickneubauer/caveOS`; this repository contains no generated website or private CaveOS content.

**Preparation state, 26 October 2026:** production still publishes from the existing FlowLoop source repository. CaveOS’s public boundary is owner-approved and integrated on its main; the FlowLoop migration remains a draft until cutover. Owner-configured credentials, Pages Actions source, main protections and environment branch restrictions are verified. Credential-backed prepared-site validation and a CaveOS requester smoke test passed; publication switches remain absent/off. Domain transfer and source privacy still require separate approval. See [validation evidence](docs/validation.md).

## Local assembly

Python 3.9+ and Git are sufficient; no package installation or site framework is required. From this checkout:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/assemble-site.py --flowloop ../flowloop.io --caveos /path/to/caveOS --output ../preview-site --allow-unapproved-local
python3 scripts/validate-site.py --site ../preview-site --caveos /path/to/caveOS --allow-unapproved-local
python3 -m http.server 5189 --bind 127.0.0.1 --directory ../preview-site
```

`--allow-unapproved-local` is a local review escape hatch, rejected in CI. It creates an unapproved marker. Never upload this output. Production assembly requires the owner-approved policy in `caveOS/website/publication-profile.json`; it then runs the same route/asset/boundary validation before the Pages artifact upload. Use a new or empty output directory each build.

## Automation

- [Deployment workflow](.github/workflows/deploy.yml): main pushes, `repository_dispatch` (`source-updated`), and manual `workflow_dispatch`. Ignores dispatch payloads and reads current trusted `main` branches.
- [Prepared migration preflight](.github/workflows/verify-migration.yml): manual credential-backed validation of the reviewed FlowLoop branch and CaveOS main, with no upload/deploy. See [owner setup](docs/owner-setup.md).
- [Tooling checks](.github/workflows/check.yml): synthetic tests on pushes and pull requests, without private-source credentials.
- Source repository notification workflows: every `main` commit, including non-website changes, requests a rebuild once enabled. No scheduled jobs, trigger loops or generated Git commits.
- `SOURCE_BUILD_ENABLED=true` activates source reads/builds. `PAGES_DEPLOY_ENABLED=true` activates publication. Both are absent/off initially; these switches do not replace the approval policy.

See [infrastructure and operations](docs/infrastructure.md), [cutover checklist](docs/cutover.md), and [validation evidence](docs/validation.md). AI assistance was used for implementation and review; checks and remaining owner actions are recorded separately.
