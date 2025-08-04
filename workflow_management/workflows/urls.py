# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from workflows.views import WorkflowViewSet, MovementViewSet, CategoryViewSet, WorkTypeViewSet, SalesChannelViewSet

router = DefaultRouter()
router.register('workflows', WorkflowViewSet)
router.register('movements', MovementViewSet, basename='movement')
router.register('categories', CategoryViewSet)
router.register('work-types', WorkTypeViewSet)
router.register('sales-channels', SalesChannelViewSet)

urlpatterns = [
    path('', include(router.urls))
]