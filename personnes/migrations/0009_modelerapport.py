from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('personnes', '0008_action_relais'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ModeleRapport',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nom', models.CharField(max_length=100)),
                ('parametres', models.JSONField(default=dict)),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('auteur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modeles_rapports', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['nom', 'pk']},
        ),
    ]
