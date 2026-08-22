"""
Permission-aware actions.

Three roles, escalating authority:
  Operator -> can approve/reject Safe or Moderate risk only, cannot modify values
  Manager  -> can approve/reject/modify up to High risk
  Admin    -> can act on anything, including Critical risk, and can change
              the system's autonomy thresholds

There's no login system here (out of scope for a hackathon demo) — the role
is selected in the UI per action and enforced server-side on every decision,
which is the part that actually matters: the server never trusts the client
to have picked an allowed action.
"""

BAND_ORDER = ["Safe", "Moderate", "High", "Critical"]

ROLE_MAX_BAND = {
    "operator": "Moderate",
    "manager": "High",
    "admin": "Critical",
}

ROLES = list(ROLE_MAX_BAND.keys())


def normalize_role(role):
    role = (role or "operator").strip().lower()
    return role if role in ROLE_MAX_BAND else "operator"


def can_decide(role, band, decision):
    """Returns (allowed: bool, reason: str|None)."""
    role = normalize_role(role)
    max_band = ROLE_MAX_BAND[role]
    allowed_bands = BAND_ORDER[: BAND_ORDER.index(max_band) + 1]

    if band not in allowed_bands:
        return False, (
            f"{role.title()} accounts can only act on requests up to '{max_band}' risk. "
            f"This request is '{band}' — an Admin needs to decide it."
        )

    if decision == "modify" and role == "operator":
        return False, "Operator accounts can approve or reject, but cannot modify the AI's proposed value."

    return True, None


def can_change_thresholds(role):
    return normalize_role(role) == "admin"
