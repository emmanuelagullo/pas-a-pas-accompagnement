from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('personnes', '0055_releve_ahi')]

    operations = [
        migrations.RemoveField(
            model_name='informationsaccompagnement',
            name='releve_ahi',
        ),
    ]
