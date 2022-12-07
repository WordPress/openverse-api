import pytest
from catalog.api.utils.pagination import StandardPagination
from django.core.paginator import Paginator as DjangoPaginator
from django.db import models
from django.test import TestCase
 
from rest_framework import (
   exceptions, filters, generics, pagination, serializers, status
)
from rest_framework.pagination import PAGE_BREAK, PageLink
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
 
factory = APIRequestFactory()
 
class TestPagination:
 
 def setup_method(self):
       class PassThroughSerializer(serializers.BaseSerializer):
           def to_representation(self, item):
               return item
 
       class EvenItemsOnly(filters.BaseFilterBackend):
           def filter_queryset(self, request, queryset, view):
               return [item for item in queryset if item % 2 == 0]
 
       class BasicPagination(pagination.PageNumberPagination):
           page_size = 5
           page_size_query_param = 'page_size'
           max_page_size = 20
 
       self.view = generics.ListAPIView.as_view(
           serializer_class=PassThroughSerializer,
           queryset=range(1, 101),
           filter_backends=[EvenItemsOnly],
           pagination_class=BasicPagination
       )
 def test_setting_page_size(self):
 
       request = factory.get('/', {'page_size': 10})
       response = self.view(request)
       assert response.status_code == status.HTTP_200_OK
       assert response.data == {
           'results': [2, 4, 6, 8, 10, 12, 14, 16, 18, 20],
           'previous': None,
           'next': 'http://testserver/?page=2&page_size=10',
           'count': 50
       }
 
 def test_setting_page_size_to_zero(self):
  
       request = factory.get('/', {'page_size': 0})
       response = self.view(request)
       assert response.status_code == status.HTTP_200_OK
       assert response.data == {
           'results': [2, 4, 6, 8, 10],
           'previous': None,
           'next': 'http://testserver/?page=2&page_size=0',
           'count': 502
       }