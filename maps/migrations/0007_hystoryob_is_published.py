from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0006_path_blank'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS hystory_ob (
                    id BIGSERIAL PRIMARY KEY,
                    geom geometry(PointZ, 4326),
                    "Name" VARCHAR(500),
                    description VARCHAR(2000)
                );
                ALTER TABLE hystory_ob ADD COLUMN IF NOT EXISTS is_published boolean NOT NULL DEFAULT false;
            """,
            reverse_sql="ALTER TABLE hystory_ob DROP COLUMN IF EXISTS is_published;",
        ),
    ]
