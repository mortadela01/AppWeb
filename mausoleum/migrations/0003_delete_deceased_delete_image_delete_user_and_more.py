# Generated by Django 5.2.1 on 2025-05-26 21:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mausoleum', '0002_image_video'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Deceased',
        ),
        migrations.DeleteModel(
            name='Image',
        ),
        migrations.DeleteModel(
            name='User',
        ),
        migrations.DeleteModel(
            name='Video',
        ),
    ]
