from django.db import migrations


class Migration(migrations.Migration):
    """Games now come from IGDB instead of RAWG. Games saved before this keep their old RAWG
    numbers in this column, which IGDB reads as different games."""

    dependencies = [
        ('games', '0007_game_game_platforms'),
    ]

    operations = [
        migrations.RenameField(model_name='game', old_name='rawg_id', new_name='igdb_id'),
    ]
