import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0002_alter_sale_product_alter_sale_region_salesorder'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sale',
            name='ba',
        ),
        migrations.AddField(
            model_name='sale',
            name='sales_rep',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='direct_sales',
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
    ]