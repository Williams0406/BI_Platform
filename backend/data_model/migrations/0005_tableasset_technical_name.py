from django.db import migrations, models
import re
import unicodedata


def normalize(value):
    value = unicodedata.normalize("NFD", str(value or ""))
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    return (value or "table")[:180]


def populate(apps, schema_editor):
    TableAsset = apps.get_model("data_model", "TableAsset")
    used = {}
    for table in TableAsset.objects.select_related("data_source").order_by("data_source__workspace_id", "id"):
        ws = str(table.data_source.workspace_id)
        base = normalize(table.table_name)
        candidate = base
        n = 2
        bucket = used.setdefault(ws, set())
        while candidate in bucket:
            suffix = f"_{n}"
            candidate = base[:180-len(suffix)] + suffix
            n += 1
        bucket.add(candidate)
        table.technical_name = candidate
        table.save(update_fields=["technical_name"])


class Migration(migrations.Migration):
    dependencies = [("data_model", "0004_relation_model_options")]
    operations = [
        migrations.AddField(
            model_name="tableasset",
            name="technical_name",
            field=models.CharField(blank=True, db_index=True, max_length=180),
        ),
        migrations.RunPython(populate, migrations.RunPython.noop),
    ]
