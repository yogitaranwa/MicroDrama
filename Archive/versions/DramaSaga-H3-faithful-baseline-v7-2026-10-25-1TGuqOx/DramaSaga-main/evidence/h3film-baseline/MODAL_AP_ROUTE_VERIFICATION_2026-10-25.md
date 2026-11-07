# Modal AP route verification for MiniMax H3

Date: 2026-10-25
Scope: read-only verification only. No GPU launch, deploy, configuration mutation, or spend.

## License and territory evidence

Official MiniMax sources checked:

- https://design.minimax.io/h3
- https://platform.minimax.io/docs/guides/local-deploy-h3
- https://platform.minimax.io/h3-license
- https://www.minimax.io/news/minimax-h3-open-source

Official MiniMax wording found on the H3 page and self-host guide:

- The Community License is royalty-free for research and commercial use, but commercial products/services above US$20 million yearly revenue need separate written authorization.
- The open-weight license currently excludes the EU, UK, US, and South Korea.
- The self-host guide says those territories require a separate license and tells users to review the current agreement before downloading, deploying, or offering a hosted service.

The full license text mirrored at Hugging Face says "Applicable Territory" means worldwide excluding the European Union, United Kingdom, Republic of Korea, and United States, and prohibits use, reproduction, modification, distribution, running, or display of the Works or Outputs outside that territory. The Hugging Face copy is secondary; the official MiniMax pages above confirm the same territory scope.

India is not one of the named excluded territories, but the license text governs running and hosting, not only the user's physical location. A compliant self-hosted route therefore needs model execution and H3 Works/Outputs handling to stay outside the excluded territories.

## Modal account access verified

Signed-in Modal dashboard and same-origin read-only API for `project-contributor`, checked 2026-10-25 about 1:39 PM IST:

- Plan: Starter.
- GPU limit: 10; active GPUs: 0.
- Container limit: 100; active containers: 0.
- `regionSelectionEnabled`: `false`.
- `cpuRegionSelectionEnabled`: `false`.
- Current cycle credits: $30.00; credits applied: $2.01; credits remaining: $27.99; cycle charges: $0.
- Current dashboard usage summary: total usage $2.01, total spend $0.

This account-level result overrides the public pricing page for current capability: the public pricing page advertises region selection on Starter, but this workspace's actual API says region selection is not enabled.

## Modal routing/storage evidence

Modal documentation checked:

- https://modal.com/docs/guide/region-selection
- https://modal.com/docs/guide/data-residency
- https://modal.com/docs/guide/functions
- https://modal.com/pricing

Relevant current statements:

- By default, Function containers can start anywhere in Modal's global fleet.
- Default Function routing is `us-east` in Virginia, USA.
- AP container regions exist in the product model (`ap`, `ap-south`, etc.), and `ap-south` routing is Mumbai, India.
- Region pinning is strict when enabled, but region selection applies a pricing multiplier: broad region 1.15x; narrow region 1.75x.
- Payloads over 2 MiB and spawned/asynchronous call payloads of any size are stored in the United States.
- Application logs are stored in the United States.
- Data written to Volumes, Images, Dicts, Queues, and Secrets is stored in the United States.

## Fit to the current H3 architecture

The current corrective architecture is not a verified applicable-territory Modal route:

- The four H3 weight files total about 42.47 GB and are stored in a Modal Volume, which Modal documents as US storage.
- The baseline render payload contains about 20.5 MB of reference images plus about 1.16 MB of audio, and the returned MP4 is about 3.1-3.9 MB; these exceed Modal's 2 MiB routing-region threshold and are stored in the US under the documented Function payload rule.
- The current workspace cannot pin an AP container or routing region because `regionSelectionEnabled` is `false`.
- AP GPU availability for RTX PRO 6000 or B200 cannot be verified without region access and a launch, so no AP capacity is confirmed.

## Conclusion

No verified supported Modal route is currently available for the next H3 generation. The actual blocker is account/route capability and architecture residency, not a generic requirement for "separate written model-license clearance":

1. This Modal workspace has region selection disabled.
2. The current H3 setup stores H3 weights and large input/output payloads in US-backed Modal storage.
3. A compliant Modal design would need region access plus a different storage/I/O design that keeps H3 Works and Outputs out of excluded territories, then AP GPU availability verification. That route is not verified and should not be offered as ready.

## Cost state and non-estimate

- Both authorized one-test windows were consumed: 10:06 IST and 12:46 IST.
- Parent-supplied latest test cost: $1.08007132.
- Current signed-in dashboard read at 1:39 PM IST: $2.01 credits applied, $27.99 credits remaining, $0 charges.
- Current public RTX PRO 6000 rate: $0.000842/second ($3.0312/hour). Region multipliers are 1.15x broad and 1.75x narrow when region selection is available.
- Because the AP route is unavailable and AP GPU capacity is unverified, there is no valid actionable AP estimated total or one-credit approval amount to ask for now.
