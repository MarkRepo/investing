<!-- prompt_version: phase2-v1 -->

# Ingest Claim Match Decision Prompt

You are filling `data/pending/match-<source_id>.json` after Python produced deterministic top_matches. Do not call tools that modify the registry. Your job is semantic judgment only.

## Inputs

1. `match-<source_id>.json`
2. The original review bundle used to generate it
3. Optional surrounding project context supplied by the user

## Output rule

Return the same JSON object with only these fields changed inside each `decisions_required[]` item:

- `decision`: one of `attach`, `new`, `split`, `skip`
- `decision_reason`: one concise sentence
- `direction_on_claim`: required only for `attach`; one of `strengthens`, `weakens`, `neutral`
- `target_claim_id`: required only for `attach`
- `split_instructions`: required only for `split`

Do not change `candidate_payload`, `top_matches`, `summary_stats`, `source_id`, `generated_at`, `bundle_ref`, or `matching_engine_version`.

## Decision rules

Choose `attach` when the candidate is the same semantic claim as an existing top_match and only adds evidence. Set `target_claim_id` to the existing claim. Set `direction_on_claim` by judging how the new evidence affects the existing claim: `strengthens`, `weakens`, or `neutral`.

Choose `new` when no top_match is the same semantic claim. Do not set `direction_on_claim`. Do not set `split_instructions`.

Choose `split` only when an existing claim is too broad or conflates multiple ideas, and this candidate makes the split necessary. Set:

```json
{
  "retire_target_claim_id": "clm-company-0001",
  "new_claims": [
    {
      "claim_text": "specific replacement claim",
      "evidence_subset": {"block_ids": ["ib-001"], "fact_ids": ["fact-001"]}
    }
  ]
}
```

Choose `skip` when the candidate is too weak, duplicate noise, or not useful as a persistent claim. `decision_reason` must say why.

## Hard constraints

- Python apply will only produce claim statuses `active` and `retired`.
- Attach does not change confidence or state_log.
- Split does not migrate historical evidence from the retired claim.
- Do not invent claim IDs.
- Do not add archive decisions here; archive approval uses `archive-writes-<source_id>.json` later.
