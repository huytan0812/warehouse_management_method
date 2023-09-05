from django.apps import AppConfig
from django.db.models.signals import post_delete

class MajorFeaturesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'major_features'

    def ready(self):
        import major_features.signals