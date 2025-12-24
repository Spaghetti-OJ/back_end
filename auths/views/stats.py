from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from submissions.models import Submission
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()

class UserSubmissionActivityView(APIView):
    """
    Get user's daily submission counts for the past year.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        try:
            target_user = get_object_or_404(User, id=user_id)
            
            # Use strict permission: currently only allow viewing own stats or if admin
            # The user didn't specify public profile, so safe default is private/admin only.
            # But the requirement is "like github", which suggests public. 
            # Given backend context usually defaulting to private unless specified:
            # allowing any authenticated user to query any user seems okay for a "profile" page feature if it's meant to be public features.
            # But safe bet: allow anyone to view anyone's stats (GitHub style public profile).
            
            # Calculate date range: last 365 days
            end_date = timezone.now()
            start_date = end_date - timedelta(days=365)

            # Query submissions
            daily_counts = (
                Submission.objects.filter(
                    user=target_user,
                    created_at__gte=start_date,
                    created_at__lte=end_date
                )
                .annotate(date=TruncDate('created_at'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )

            # Convert to dictionary { "YYYY-MM-DD": count }
            # Only sending days with activity to reduce payload size
            data = {entry['date'].strftime('%Y-%m-%d'): entry['count'] for entry in daily_counts}

            return Response({
                "status": "success",
                "data": data,
                "message": "Submission activity retrieved successfully."
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "status": "error", 
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
