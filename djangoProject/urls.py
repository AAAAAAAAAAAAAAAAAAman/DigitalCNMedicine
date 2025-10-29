"""djangoProject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from medicine import views

urlpatterns = [

    path('stream-chat/', views.api_stream_chat_response, name='stream_chat'),
    path('medicine_ai/', views.medicine_ai),  # AI chat页面
    path('internet_search_view/', views.internet_search_view, name='internet_search_view'),  # 联网搜索结果预览页面
    path('index/', views.index),
    path('login/', views.login),
    path('logout/', views.logout),
    path('passageindex/', views.passageindex),
    path('getpassage/', views.getpassage),
    path('searchresult/', views.searchresult),
    path('model_kg/', views.model_kg),

    path('submitsatisfaction/', views.submitsatisfaction),

    path('sendemail/', views.sendemail),
    path('subscribe/', views.subscribe),
    path('register/', views.register),
    path('recommend/', views.recommend),
    path('qs/', views.qs),
    path('root_medicine_ai/', views.root_medicine_ai),
    path('root_index/', views.root_index),





    #  测试页面，

    path('single/', views.single),
    #  测试页面，测试从neo4j查询数据并用echarts可视化到html
    path('model_kg_test/', views.model_kg_test),
    #  测试页面，功能是输入问题，调用大模型并将大模型回答实时流式推送到html
    path('stream_test/', views.stream_test, name='stream_test'),
    path('api_stream_test/', views.api_stream_test, name='api_stream_test'),

    # path('admin/', admin.site.urls),
]
