import re
from pathlib import Path

from app import create_app

app = create_app()

valid_endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}

endpoint_replacements = {
    "login": "auth.login",
    "register": "auth.register",
    "logout": "auth.logout",

    "sessions": "session.sessions",
    "new_session": "session.new_session",
    "start_workout": "session.start_workout",
    "view_session": "session.view_session",
    "edit_session": "session.edit_session",
    "delete_session": "session.delete_session",
    "add_exercise": "session.add_exercise",
    "edit_exercise": "session.edit_exercise",
    "delete_exercise": "session.delete_exercise",

    "macros": "meal.macros",
    "add_meal": "meal.add_meal",
    "edit_meal": "meal.edit_meal",
    "delete_meal": "meal.delete_meal",

    "prs": "pr.prs",
    "new_pr": "pr.new_pr",
    "edit_pr": "pr.edit_pr",
    "delete_pr": "pr.delete_pr",

    "prediction": "prediction.prediction",

    "admin_debug": "admin.admin_debug",
    "cleanup_orphans": "admin.cleanup_orphans",
}

search_folders = [
    Path("templates"),
    Path("routes"),
]

pattern = re.compile(r"url_for\(\s*['\"]([^'\"]+)['\"]")

problems_found = False

print("\nVALID FLASK ENDPOINTS")
print("---------------------")
for endpoint in sorted(valid_endpoints):
    print(endpoint)

print("\nBROKEN OR OLD url_for() REFERENCES")
print("----------------------------------")

for folder in search_folders:
    if not folder.exists():
        continue

    for path in folder.rglob("*"):
        if path.suffix not in [".html", ".py"]:
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            matches = pattern.findall(line)

            for endpoint in matches:
                if endpoint in valid_endpoints:
                    continue

                problems_found = True

                suggestion = endpoint_replacements.get(endpoint)

                if not suggestion:
                    suffix_matches = [
                        valid_endpoint
                        for valid_endpoint in valid_endpoints
                        if valid_endpoint.endswith("." + endpoint)
                    ]

                    if len(suffix_matches) == 1:
                        suggestion = suffix_matches[0]

                print(f"\n{path}:{line_number}")
                print(f"  OLD: url_for('{endpoint}')")

                if suggestion:
                    print(f"  NEW: url_for('{suggestion}')")
                else:
                    print("  NEW: No automatic suggestion found. Check the valid endpoints list above.")

if not problems_found:
    print("No broken endpoint names found.")
