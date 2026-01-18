from django.urls import path
from .views import *

urlpatterns = [
    # Public / auth
    path('', home, name='home'),
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # User area
    path('predict/', predict_view, name='predict'),
    path('history/', user_history_view, name='user_history'),
    path('history/<int:pk>/delete/', user_delete_prediction, name='user_delete_prediction'),

    path('profile/', profile_view, name='profile'),
    path('change-password/', change_password_view, name='change_password'),

    # Admin area (custom panel)
    path('admin-login/', admin_login_view, name='admin_login'),
    path('admin/dashboard/',admin_dashboard_view, name='admin_dashboard'),
    path('admin/users/',admin_users_view, name='admin_users'),
    path('admin/predictions/', admin_predictions_view, name='admin_predictions'),

    # JSON API stays as earlier
    path('api/predict/',predict_api, name='predict_api'),
    path('admin/users/<int:user_id>/delete/', admin_delete_user, name='admin_delete_user'),
path('admin/predictions/<int:pk>/delete/', admin_delete_prediction, name='admin_delete_prediction'),
path('history/export-csv/', user_history_export_csv, name='user_history_export_csv'),

# Admin exports
path('admin/export/users.csv', admin_export_users_csv, name='admin_export_users_csv'),
path('admin/export/predictions.csv', admin_export_predictions_csv, name='admin_export_predictions_csv'),



]


# urlpatterns = [
#     path('', predict_view, name='predict'),
#     path('api/predict/', predict_api, name='predict_api'),
# ]
