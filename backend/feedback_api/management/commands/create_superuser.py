from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Creates a superuser and adds it to the Moderators group'

    def handle(self, *args, **kwargs):
        # Create superuser
        try:
            superuser = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpassword'
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{superuser.username}' created successfully!"))
        except IntegrityError:
            superuser = User.objects.get(username='admin')
            self.stdout.write(self.style.WARNING("Superuser already exists."))
        
        # Create Moderators group if it doesn't exist
        moderators_group, created = Group.objects.get_or_create(name='Moderators')
        if created:
            self.stdout.write(self.style.SUCCESS("Moderators group created."))
        else:
            self.stdout.write(self.style.WARNING("Moderators group already exists."))
        
        # Add superuser to Moderators group
        if superuser not in moderators_group.user_set.all():
            moderators_group.user_set.add(superuser)
            self.stdout.write(self.style.SUCCESS(f"Added {superuser.username} to Moderators group."))
        else:
            self.stdout.write(self.style.WARNING(f"{superuser.username} is already in Moderators group."))
