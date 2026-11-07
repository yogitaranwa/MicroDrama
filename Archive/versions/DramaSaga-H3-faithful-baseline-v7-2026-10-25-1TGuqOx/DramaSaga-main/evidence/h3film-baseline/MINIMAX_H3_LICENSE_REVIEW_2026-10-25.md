# MiniMax H3 license review

Date: 2026-10-25

## Sources checked

- Repackaged ComfyUI model card: https://huggingface.co/Comfy-Org/MiniMax-H3/raw/main/README.md
- Upstream license named by that card: https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE
- Modal region documentation: https://modal.com/docs/guide/region-selection

The Comfy-Org card declares `license: other`, `license_name: minimax-h3-community-license-agreement`, and points to the upstream MiniMax license above.

## Observed terms relevant to a private test

- The license grants a non-exclusive, non-transferable, royalty-free, limited license to use, reproduce, distribute, create derivative works, and modify the materials, but only within the "Applicable Territory".
- "Applicable Territory" is worldwide excluding the European Union, the United Kingdom, the Republic of Korea, and the United States of America.
- Use, reproduction, modification, distribution, or display of the MiniMax H3 Works or Outputs outside the Applicable Territory is not authorized by the agreement.
- The separate prior written authorization clause applies only when commercial products and services generate more than USD 20 million in yearly revenue. A private test under that threshold does not trigger that specific clause.
- Outputs are not Model Derivatives; MiniMax claims no rights over Outputs, and the user remains responsible for Outputs and subsequent use.
- Use must comply with applicable law and the MiniMax Acceptable Use Policy. Third-party intellectual-property restrictions, including Harry Potter rights, are separate from this model license.
- Providing third-party access to a product, service, or hosted service has extra recipient-terms and safeguard requirements. That is not the same as a private test.

## Correction to prior guard wording

The phrase "pending separate written model-license clearance" was conservative internal wording, not a clause found in the checked model-owner terms. It should not be presented as an external requirement for the user's private test.

The genuine model-license issue is narrower: the user is in India, which is within the Applicable Territory, but a cloud run must also avoid execution/use in an excluded territory. The previous Modal app did not pin a region in code and the prior GPU's physical region was not evidenced in the retained artifacts. Modal's region documentation says that, by default, Function containers can start anywhere in its global fleet and inputs are routed through Virginia, USA (`us-east`); container/routing region constraints are available but can affect pricing and scheduling. A future Modal launch needs an applicable-territory execution route. Read-only verification on 2026-10-25 found this workspace has `regionSelectionEnabled: false`, and the current Volume/large-payload architecture stores H3 Works and Outputs in US-backed Modal storage. No verified Modal AP route is currently available. This is a territory/compliance check, not a blanket requirement for separate written MiniMax clearance.

## Current execution authority

The user approved one corrected Modal test with $0 net card spend on 2026-10-25 at 10:06 IST. That one test has already run and the approval window is consumed. There is no current approval for another render, batch, GPU launch, card charge, or credit spend.
