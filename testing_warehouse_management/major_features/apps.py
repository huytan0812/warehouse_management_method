from django.apps import AppConfig


class MajorFeaturesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'major_features'

    def ready(self):
        import testing_warehouse_management.major_features.signals