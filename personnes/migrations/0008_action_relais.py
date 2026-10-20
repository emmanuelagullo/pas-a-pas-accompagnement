from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("personnes", "0007_transmissions_notes"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="ActionRelais", fields=[
        ("id", models.BigAutoField(primary_key=True, serialize=False)),
        ("libelle", models.CharField(max_length=240)),
        ("cree_le", models.DateTimeField(auto_now_add=True)),
        ("echeance", models.DateField(null=True, blank=True)),
        ("terminee_le", models.DateTimeField(null=True, blank=True)),
        ("auteur", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="actions_relais_creees", to=settings.AUTH_USER_MODEL)),
        ("terminee_par", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="actions_relais_terminees", to=settings.AUTH_USER_MODEL)),
    ], options={"ordering": ["echeance", "cree_le", "pk"]})]
