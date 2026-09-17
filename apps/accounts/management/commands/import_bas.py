from django.core.management.base import BaseCommand, CommandError
from apps.accounts.bulk_import import import_users_from_csv


class Command(BaseCommand):
    help = "Bulk-import Brand Ambassadors (or Supervisors) from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    def handle(self, *args, **options):
        path = options["csv_path"]
        try:
            f = open(path, "r", encoding="utf-8-sig")
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")

        with f:
            result = import_users_from_csv(f)

        self.stdout.write(self.style.SUCCESS(f"Created {len(result.created)} users."))
        if result.created:
            self.stdout.write("\nusername,temp_password,role,region,supervisor")
            for u in result.created:
                self.stdout.write(
                    f"{u['username']},{u['temp_password']},{u['role']},"
                    f"{u['region'] or ''},{u['supervisor_username'] or ''}"
                )
            self.stdout.write(self.style.WARNING(
                "\nSave the temp passwords above now — they are not stored anywhere "
                "and cannot be recovered. Each user must change their password on first login."
            ))

        if result.errors:
            self.stdout.write(self.style.ERROR(f"\n{len(result.errors)} row(s) failed:"))
            for e in result.errors:
                self.stdout.write(self.style.ERROR(f"  row {e['row']}: {e['error']}"))
