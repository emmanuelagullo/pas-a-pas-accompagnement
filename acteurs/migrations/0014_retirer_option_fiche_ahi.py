from django.db import migrations


def retirer_option(apps, schema_editor):
    Service = apps.get_model('acteurs', 'Service')
    services = Service.objects.using(schema_editor.connection.alias)
    for service in services.all().iterator():
        if 'fiche_ahi' in service.profil_collectif:
            service.profil_collectif.pop('fiche_ahi')
            service.save(using=schema_editor.connection.alias, update_fields=['profil_collectif'])


class Migration(migrations.Migration):
    dependencies = [('acteurs', '0013_listes_saisie')]

    operations = [migrations.RunPython(retirer_option, migrations.RunPython.noop)]
