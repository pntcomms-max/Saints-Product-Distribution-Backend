"""
Shared CSV bulk-import logic for onboarding Brand Ambassadors (or
Supervisors) at scale. Used by both the management command
(`import_bas.py`) and the API endpoint (`UserViewSet.bulk_import`), so
the two never drift apart.

Expected CSV columns (header row required):
    first_name, last_name, username, phone, region, supervisor_username, role

- `username` must be unique; if blank, one is generated from the name.
- `region` is looked up by name; created automatically if it doesn't exist.
- `supervisor_username` is optional — leave blank for supervisors/managers,
  or if you'll assign supervisors later in bulk.
- `role` is optional, defaults to BA. Valid values: BA, SUPERVISOR, MANAGER.

Each created user gets a random temporary password and
`must_change_password=True`, so nothing permanent ships over a CSV.
"""
import csv
import io
import secrets
from dataclasses import dataclass, field

from django.db import transaction

from apps.catalog.models import Region
from .models import User


@dataclass
class ImportResult:
    created: list = field(default_factory=list)   # [{"username":..., "temp_password":...}]
    errors: list = field(default_factory=list)     # [{"row": n, "error": "..."}]

    @property
    def summary(self):
        return {"created_count": len(self.created), "error_count": len(self.errors),
                "created": self.created, "errors": self.errors}


def _make_username(first, last, row_num):
    base = f"{first}.{last}".lower().replace(" ", "")
    base = base or f"ba{row_num}"
    candidate = base
    n = 1
    while User.objects.filter(username=candidate).exists():
        n += 1
        candidate = f"{base}{n}"
    return candidate


def import_users_from_csv(file_like) -> ImportResult:
    """
    `file_like` is any file-like object opened in text mode (or bytes,
    which we decode) — works with an open() handle from the management
    command or request.FILES['file'] from the API.
    """
    result = ImportResult()

    raw = file_like.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")  # tolerate Excel's BOM
    reader = csv.DictReader(io.StringIO(raw))

    required_cols = {"first_name", "last_name"}
    if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
        result.errors.append({"row": 0, "error": f"CSV must include columns: {', '.join(required_cols)}"})
        return result

    for row_num, row in enumerate(reader, start=2):  # row 1 is the header
        try:
            with transaction.atomic():
                first = (row.get("first_name") or "").strip()
                last = (row.get("last_name") or "").strip()
                if not first or not last:
                    raise ValueError("first_name and last_name are required")

                username = (row.get("username") or "").strip() or _make_username(first, last, row_num)
                if User.objects.filter(username=username).exists():
                    raise ValueError(f"username '{username}' already exists")

                role = (row.get("role") or "BA").strip().upper()
                if role not in dict(User.Role.choices):
                    raise ValueError(f"invalid role '{role}'")

                region = None
                region_name = (row.get("region") or "").strip()
                if region_name:
                    region, _ = Region.objects.get_or_create(name=region_name)

                supervisor = None
                sup_username = (row.get("supervisor_username") or "").strip()
                if sup_username:
                    try:
                        supervisor = User.objects.get(username=sup_username, role=User.Role.SUPERVISOR)
                    except User.DoesNotExist:
                        raise ValueError(f"supervisor_username '{sup_username}' not found (or not a supervisor)")

                temp_password = secrets.token_urlsafe(8)
                user = User(
                    username=username, first_name=first, last_name=last,
                    phone=(row.get("phone") or "").strip(), role=role,
                    region=region, supervisor=supervisor, must_change_password=True,
                )
                user.set_password(temp_password)
                user.save()

                result.created.append({
                    "row": row_num, "username": username, "full_name": f"{first} {last}",
                    "role": role, "region": region_name or None,
                    "supervisor_username": sup_username or None, "temp_password": temp_password,
                })
        except Exception as e:
            result.errors.append({"row": row_num, "error": str(e)})

    return result
