from django.urls import path

from ..views import import_csv as import_csv_views

app_name = "import_csv"

urlpatterns = [
    path(
        "",
        import_csv_views.CourseImportCSVView.as_view(),
        name="import_csv",
    ),
]
