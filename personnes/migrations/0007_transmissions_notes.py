from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("personnes", "0006_menage_revision_correctionperiode_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name="Transmission", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False)),
            ("contenu", models.TextField()),
            ("cree_le", models.DateTimeField(auto_now_add=True)),
            ("auteur", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-cree_le", "-pk"]}),
        migrations.CreateModel(name="NotePartagee", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False)),
            ("contenu", models.TextField()),
            ("cree_le", models.DateTimeField(auto_now_add=True)),
            ("auteur", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ("personne", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notes", to="personnes.personne")),
            ("accompagnement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notes", to="personnes.accompagnement")),
            ("sejour", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notes", to="personnes.sejour")),
        ], options={"ordering": ["-cree_le", "-pk"]}),
        migrations.CreateModel(name="RevisionContribution", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False)),
            ("date", models.DateTimeField(auto_now_add=True)),
            ("ancien_texte", models.TextField()),
            ("nouveau_texte", models.TextField()),
            ("motif", models.TextField()),
            ("auteur", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ("transmission", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="revisions", to="personnes.transmission")),
            ("note", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="revisions", to="personnes.notepartagee")),
        ], options={"ordering": ["date", "pk"]}),
        migrations.AddConstraint(model_name="notepartagee", constraint=models.CheckConstraint(
            condition=(models.Q(personne__isnull=False, accompagnement__isnull=True, sejour__isnull=True)
                       | models.Q(personne__isnull=True, accompagnement__isnull=False, sejour__isnull=True)
                       | models.Q(personne__isnull=True, accompagnement__isnull=True, sejour__isnull=False)),
            name="note_exactement_une_cible")),
        migrations.AddConstraint(model_name="revisioncontribution", constraint=models.CheckConstraint(
            condition=(models.Q(transmission__isnull=False, note__isnull=True)
                       | models.Q(transmission__isnull=True, note__isnull=False)), name="revision_une_cible")),
    ]
