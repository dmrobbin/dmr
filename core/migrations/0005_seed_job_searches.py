from django.db import migrations

STARTING_SEARCHES = [
    "senior software engineer",
    "software engineer",
]


def add_searches(apps, schema_editor):
    JobSearch = apps.get_model("core", "JobSearch")
    for query in STARTING_SEARCHES:
        JobSearch.objects.get_or_create(query=query, location="", remote_only=True)


def remove_searches(apps, schema_editor):
    apps.get_model("core", "JobSearch").objects.filter(query__in=STARTING_SEARCHES, location="").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_joblead_import_fields"),
    ]

    operations = [
        migrations.RunPython(add_searches, remove_searches),
    ]
