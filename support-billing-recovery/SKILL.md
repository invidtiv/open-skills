---
name: support-billing-recovery
version: 1.0.0
description: >
  Recover a stuck billing charge for a support ticket: identify the charge,
  verify the failure mode, issue the refund or retry, document the resolution,
  and close the loop with the customer. Designed to work identically whether
  the agent runs in Hermes, Claude Code, Cursor, Codex, or a generic shell.
category: operations
tags: [billing, support, refunds, stripe, customer-success]
author: you@yourdomain.com
license: MIT
created: 2026-06-19
updated: 2026-06-19
min_agent_capability: tool-use
---

# Support Billing Recovery

This is the procedure, not the prompt. It survives a model change, a tool
switch, and a new hire's first day. It is yours.

## Trigger

Activate this skill when any of the following are true:

- A support ticket mentions "stuck charge", "duplicate billing", "failed payment", or "refund request"
- A customer reports being charged but not receiving the service
- A billing alert fires for a charge in `failed` or `pending` state > 4 hours
- A teammate asks "how do I handle a billing recovery?"

Do not activate for general billing questions, plan changes, or subscription
upgrades — those are different skills.

## Prerequisites

Before starting, verify:

1. **Stripe CLI** is installed and authenticated
   - Check: `stripe --version` (must return a version string)
   - Check: `stripe status` (must show "Authenticated")
2. **Stripe API key** is in the environment
   - Check: `echo $STRIPE_API_KEY | wc -c` (must be > 10)
   - If missing: stop and ask the operator to set `STRIPE_API_KEY`
3. **Support ticket system** is accessible
   - Check: `curl -sf -H "Authorization: Bearer $SUPPORT_TICKET_API_KEY" $SUPPORT_TICKET_API_URL/health`
   - If unreachable: proceed with billing recovery but note that ticket
     cannot be updated automatically
4. **Customer email** is known from the ticket
   - If missing: use the Stripe customer ID instead and look up email later

If any prerequisite fails, do not proceed — ask the operator to resolve it.

## Procedure

### Step 1: Identify the charge

```bash
# Find the customer in Stripe
stripe customers list --email="${CUSTOMER_EMAIL}" --format=json > /tmp/billing-recovery/customer.json

# Extract customer ID
CUSTOMER_ID=$(python3 -c "import json; d=json.load(open('/tmp/billing-recovery/customer.json')); print(d['data'][0]['id'] if d['data'] else 'NOT_FOUND')")

if [ "$CUSTOMER_ID" = "NOT_FOUND" ]; then
    echo "No Stripe customer found for ${CUSTOMER_EMAIL}"
    exit 1
fi

# List recent charges for this customer
stripe charges list --customer="${CUSTOMER_ID}" --limit=10 --format=json > /tmp/billing-recovery/charges.json
```

### Step 2: Verify the failure

```bash
# Find charges in failed or pending state
python3 << 'PYEOF'
import json, sys
charges = json.load(open('/tmp/billing-recovery/charges.json'))
failed = [c for c in charges['data'] if c['status'] in ('failed', 'pending')]
if not failed:
    print("No failed or pending charges found — nothing to recover.")
    sys.exit(0)
for c in failed:
    print(f"  CHARGE: {c['id']}  STATUS: {c['status']}  AMOUNT: {c['amount']}  CREATED: {c['created']}")
    print(f"    FAILURE: {c.get('failure_message', 'N/A')}")
    print(f"    FAILURE_CODE: {c.get('failure_code', 'N/A')}")
# Save the most recent failed charge for recovery
latest = failed[0]
with open('/tmp/billing-recovery/target-charge.json', 'w') as f:
    json.dump(latest, f, indent=2)
print(f"\nTarget charge: {latest['id']}")
PYEOF
```

### Step 3: Decide — refund or retry

Read `/tmp/billing-recovery/target-charge.json` and decide:

- **If `failure_code` is `insufficient_funds` or `card_declined`**: → retry with
  a different payment method (Step 4a)
- **If `failure_code` is `expired_card` or `processing_error`**: → refund and
  notify (Step 4b)
- **If the charge is `pending` but > 4 hours old**: → refund (stuck pending
  charges rarely resolve)
- **If the charge actually succeeded** but the customer didn't get the service:
  → this is a different skill (service-fulfillment-recovery), not this one

### Step 4a: Retry with new payment method

```bash
# Ask the operator to provide a new payment method token
echo "Operator: provide a new payment method token for customer ${CUSTOMER_ID}"
read NEW_PAYMENT_TOKEN

# Create a new charge with the new payment method
stripe charges create \
    --amount="$(python3 -c "import json; print(json.load(open('/tmp/billing-recovery/target-charge.json'))['amount'])")" \
    --currency=usd \
    --customer="${CUSTOMER_ID}" \
    --source="${NEW_PAYMENT_TOKEN}" \
    --description="Retry charge for support ticket" \
    --format=json > /tmp/billing-recovery/retry-charge.json

# Verify the retry succeeded
RETRY_STATUS=$(python3 -c "import json; print(json.load(open('/tmp/billing-recovery/retry-charge.json'))['status'])")
if [ "$RETRY_STATUS" = "succeeded" ]; then
    echo "✓ Retry charge succeeded"
else
    echo "✗ Retry charge failed with status: ${RETRY_STATUS}"
    echo "  Falling back to refund path"
    # Go to Step 4b
fi
```

### Step 4b: Issue the refund

```bash
# Refund the failed charge
CHARGE_ID=$(python3 -c "import json; print(json.load(open('/tmp/billing-recovery/target-charge.json'))['id'])")

stripe refunds create --charge="${CHARGE_ID}" --format=json > /tmp/billing-recovery/refund.json

# Verify the refund
REFUND_STATUS=$(python3 -c "import json; print(json.load(open('/tmp/billing-recovery/refund.json'))['status'])")
if [ "$REFUND_STATUS" = "succeeded" ]; then
    echo "✓ Refund succeeded for charge ${CHARGE_ID}"
elif [ "$REFUND_STATUS" = "pending" ]; then
    echo "⚠ Refund is pending — this is normal for some payment methods"
else
    echo "✗ Refund failed with status: ${REFUND_STATUS}"
    # Do NOT proceed to step 5 — escalate manually
    echo "  Escalate to billing engineering team"
    exit 1
fi
```

### Step 5: Document the resolution

```bash
# Create the resolution record
python3 << 'PYEOF'
import json, datetime
charge = json.load(open('/tmp/billing-recovery/target-charge.json'))
refund = json.load(open('/tmp/billing-recovery/refund.json')) if __import__('os').path.exists('/tmp/billing-recovery/refund.json') else None
retry = json.load(open('/tmp/billing-recovery/retry-charge.json')) if __import__('os').path.exists('/tmp/billing-recovery/retry-charge.json') else None

resolution = {
    "ticket_id": __import__('os').environ.get("TICKET_ID", "unknown"),
    "customer_email": __import__('os').environ.get("CUSTOMER_EMAIL", "unknown"),
    "charge_id": charge["id"],
    "charge_amount": charge["amount"],
    "failure_code": charge.get("failure_code"),
    "failure_message": charge.get("failure_message"),
    "action_taken": "refund" if refund else ("retry" if retry else "none"),
    "refund_id": refund["id"] if refund else None,
    "refund_status": refund["status"] if refund else None,
    "retry_charge_id": retry["id"] if retry else None,
    "retry_status": retry["status"] if retry else None,
    "resolved_at": datetime.datetime.utcnow().isoformat(),
    "resolved_by": "open-skill: support-billing-recovery v1.0.0"
}
with open('/tmp/billing-recovery/resolution.json', 'w') as f:
    json.dump(resolution, f, indent=2)
print(json.dumps(resolution, indent=2))
PYEOF
```

### Step 6: Close the loop

```bash
# Update the support ticket (if API is available)
if curl -sf -H "Authorization: Bearer $SUPPORT_TICKET_API_KEY" "$SUPPORT_TICKET_API_URL/health" >/dev/null 2>&1; then
    curl -sf -X POST \
        -H "Authorization: Bearer $SUPPORT_TICKET_API_KEY" \
        -H "Content-Type: application/json" \
        -d @/tmp/billing-recovery/resolution.json \
        "$SUPPORT_TICKET_API_URL/tickets/${TICKET_ID}/resolve"
    echo "✓ Ticket ${TICKET_ID} updated"
else
    echo "⚠ Support ticket API unavailable — resolution saved to /tmp/billing-recovery/resolution.json"
    echo "  Manual ticket update required"
fi

# Send customer notification email (optional, if email tool is available)
echo "Customer ${CUSTOMER_EMAIL} — your billing issue has been resolved."
echo "Resolution details are in /tmp/billing-recovery/resolution.json"
```

## Pitfalls

- **Don't refund a succeeded charge**: If the charge status is `succeeded`,
  the customer's issue is service delivery, not billing. This is a different
  skill. Refunding a succeeded charge creates a new problem.

- **Don't retry the same payment method**: If a card was declined, retrying
  the same card will fail again. Always ask for a new payment method token.

- **Pending charges can resolve on their own**: If the charge is `pending` and
  < 4 hours old, wait before refunding. Stripe's 4-hour threshold is the
  industry standard for "stuck" pending charges.

- **Refund amounts must match the original charge**: Don't issue partial
  refunds unless the customer explicitly requests one. Partial refunds create
  accounting discrepancies.

- **Always save the resolution JSON**: Even if the ticket API is down, the
  resolution record must be persisted. Without it, the recovery is
  unverifiable.

## Verification

Confirm the skill worked by checking ALL of the following:

1. `/tmp/billing-recovery/resolution.json` exists and is valid JSON
2. The `action_taken` field is either `"refund"` or `"retry"` (not `"none"`)
3. If `action_taken` is `"refund"`: `refund_status` is `"succeeded"` or `"pending"`
4. If `action_taken` is `"retry"`: `retry_status` is `"succeeded"`
5. The support ticket is updated (or a manual update is documented)
6. The customer has been notified

Run the verification script:

```bash
python3 tests/test_basic.py --verify
```

If any verification fails, the recovery is not complete. Do not mark the
ticket as resolved. Escalate to billing engineering.

## Recovery (when this skill itself fails)

If the skill fails at any step:

1. **Stripe CLI not authenticated**: Run `stripe login` and retry from Step 1
2. **Charge not found**: The customer may have a different email in Stripe.
   Search by name or phone instead: `stripe customers list --text-search="${CUSTOMER_NAME}"`
3. **Refund fails**: Do not retry the refund automatically. Escalate to
   billing engineering with the charge ID and error message.
4. **Resolution JSON cannot be written**: Check `/tmp/billing-recovery/`
   directory exists and is writable. If disk is full, write to a different
   temp directory and note the path in the ticket.
5. **Skill itself is broken**: The skill has tests. Run `openskills test`
   to identify which step is failing. If the skill is broken, it should be
   fixed in the source (not patched at runtime) and re-exported to all
   platforms.
