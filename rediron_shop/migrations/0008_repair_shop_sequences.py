from django.db import migrations


SEQUENCE_TABLES = [
    "rediron_shop_order",
    "rediron_shop_orderitem",
    "rediron_shop_cart",
    "rediron_shop_cartitem",
    "rediron_shop_wishlist",
    "rediron_shop_wishlistitem",
]


def repair_postgres_sequences(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        for table in SEQUENCE_TABLES:
            cursor.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence(%s, 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1),
                    (SELECT EXISTS(SELECT 1 FROM {table}))
                )
                """.format(table=table),
                [table],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("rediron_shop", "0007_alter_blogpost_slug_alter_brand_slug_and_more"),
    ]

    operations = [
        migrations.RunPython(repair_postgres_sequences, migrations.RunPython.noop),
    ]
