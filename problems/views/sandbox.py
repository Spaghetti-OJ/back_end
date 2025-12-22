from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.conf import settings
import os
from ..responses import api_response
from ..models import Problems

class ProblemTestCasePackageView(APIView):
    """GET /problem/<pk>/testdata (Sandbox 專用)
    目的：提供 Sandbox 下載該題目的完整測資包 (.zip)。
    驗證：query string `token`。
    回傳：application/zip 檔案流
    """
    permission_classes = []

    def get(self, request, pk: int):
        token_req = request.GET.get('token')
        # 從環境變數或 settings 讀取 SANDBOX_TOKEN
        token_expected = getattr(settings, 'SANDBOX_TOKEN', os.environ.get('SANDBOX_TOKEN'))
        
        if not token_expected or token_req != token_expected:
            return api_response(None, "Invalid sandbox token", status_code=401)

        problem = get_object_or_404(Problems, pk=pk)
        from ..services.storage import _storage
        rel = os.path.join("testcases", f"p{problem.id}", "problem.zip")
        
        if not _storage.exists(rel):
            raise Http404("Test case archive not found")
            
        fh = _storage.open(rel, 'rb')
        resp = FileResponse(fh, content_type='application/zip')
        resp["Content-Disposition"] = f"attachment; filename=\"problem-{problem.id}-package.zip\""
        return resp
