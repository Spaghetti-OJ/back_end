from django.shortcuts import render

from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from .models import Assignments
from .serializers import AssignmentCreateSerializer
from .permissions import IsTeacherOrAdminOrReadOnly

class AssignmentViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Assignments.objects.select_related("course", "creator")
    serializer_class = AssignmentCreateSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdminOrReadOnly]
