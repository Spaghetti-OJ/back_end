from django.apps import AppConfig


class SubmissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'submissions'
    
    def ready(self):
        """Import signal handlers and initialize cache"""
        import submissions.cache.signals  # noqa
        
        # Initialize bloom filter
        from submissions.cache.protection import submission_bloom_filter
        from submissions.models import Submission
        
        try:
            submission_bloom_filter.initialize_from_db(Submission, 'id')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize bloom filter: {e}")
