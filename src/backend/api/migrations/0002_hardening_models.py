#
# SPDX-License-Identifier: Apache-2.0
#
from django.db import migrations, models
import django.db.models.deletion


def delete_null_fabricresourceset(apps, schema_editor):
    FabricResourceSet = apps.get_model("api", "FabricResourceSet")
    FabricResourceSet.objects.filter(resource_set__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(delete_null_fabricresourceset, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="fabricresourceset",
            name="resource_set",
            field=models.OneToOneField(
                help_text="Resource set to which the fabric resourceset belongs",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sub_resource_set",
                to="api.resourceset",
            ),
        ),
        migrations.AlterField(
            model_name="node",
            name="agent",
            field=models.ForeignKey(
                help_text="Agent of node",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="node",
                to="api.agent",
            ),
        ),
        migrations.AlterField(
            model_name="agent",
            name="organization",
            field=models.ForeignKey(
                help_text="Organization of agent",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="agents",
                to="api.loleidoorganization",
            ),
        ),
        migrations.AlterField(
            model_name="kubernetesconfig",
            name="agent",
            field=models.ForeignKey(
                help_text="Agent of kubernetes config",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="api.agent",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="resourceset",
            unique_together={("membership", "environment")},
        ),
        migrations.AddConstraint(
            model_name="port",
            constraint=models.UniqueConstraint(
                fields=("node", "internal"), name="unique_node_internal_port"
            ),
        ),
        migrations.AddConstraint(
            model_name="port",
            constraint=models.UniqueConstraint(
                fields=("node", "external"), name="unique_node_external_port"
            ),
        ),
    ]
