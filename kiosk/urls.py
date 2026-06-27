
# from django.contrib import admin
# from django.urls import path
# from django.conf import settings
# from django.conf.urls.static import static
# from django.contrib.auth.views import LogoutView
# from core import views

# urlpatterns = [
#     path('', views.login_view, name='login'),
#     path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
#     path('dashboard/', views.dashboard_view, name='dashboard'),
#     path('api/upload/', views.upload_files_view, name='upload_files'),
#     path('api/settings/', views.save_settings_view, name='save_settings'),
#     path('admin-panel/', views.admin_panel_view, name='admin_panel'),
#     path('api/admin-action/', views.admin_action_view, name='admin_action'),
#     path('super-admin/', views.super_admin_panel, name='super_admin_panel'),
#     path('api/super-admin-action/', views.super_admin_action, name='super_admin_action'),
#     path('api/users/', views.api_users, name='api_users'),
#     path('api/send-files/', views.send_files_view, name='send_files'),
#     path('api/download-file/<int:file_id>/', views.download_file_view, name='download_file'),
#     path('api/delete-my-file/', views.delete_my_file_view, name='delete_my_file'),
    
#     # AI و امنیت
#     path('api/analyze-file/<int:file_id>/', views.analyze_file_with_ai, name='analyze_file_ai'),
#     path('api/analyze-user/<int:user_id>/', views.analyze_user_view, name='analyze_user'),
#     path('api/analyze-all-files/', views.analyze_all_files_view, name='analyze_all_files'),
#     path('api/analyze-all-users/', views.analyze_all_users_view, name='analyze_all_users'),
#     path('api/alerts/count/', views.alerts_count_view, name='alerts_count'),
#     path('api/security-stats/', views.security_stats_view, name='security_stats'),
#     path('api/my-permissions/', views.my_permissions_view, name='my_permissions'),
    
#     # مدیریت فایل و هشدارها
#     path('file-summary/<int:file_id>/', views.file_summary_view, name='file_summary'),
#     path('security-alerts/', views.security_alerts_view, name='security_alerts'),
#     path('resolve-alert/<int:alert_id>/', views.resolve_alert_view, name='resolve_alert'),
#     path('login-logs/', views.login_logs_view, name='login_logs'),
#     path('user-detail/<int:user_id>/', views.user_detail_view, name='user_detail'),
    
#     # APIهای مدیریتی
#     path('api/all-permissions/', views.get_all_permissions, name='all_permissions'),
#     path('api/roles/', views.get_all_roles, name='api_roles'),
#     path('api/all-permissions/', views.get_all_permissions, name='api_all_permissions'),
#     path('api/role-permissions/<int:role_id>/', views.get_role_permissions, name='api_role_permissions'),
#     path('api/save-role-permissions/', views.save_role_permissions, name='api_save_role_permissions'),
#     path('api/create-role/', views.create_new_role, name='api_create_role'),
#     path('api/users-list/', views.get_users_list, name='api_users_list'),
#     path('api/set-password-policy/', views.set_password_policy, name='api_set_password_policy'),
#     path('api/toggle-block/<int:user_id>/', views.toggle_block_user, name='api_toggle_block'),
#     path('api/delete-user/<int:user_id>/', views.delete_user_by_id, name='api_delete_user'),
    
#     # تحلیل شخصیت
#     path('api/analyze-user-personality/<int:user_id>/', views.analyze_user_personality_view, name='analyze_user_personality'),
    
#     # ========== اضافه کردن آدرس تنظیمات AI ==========
#     path('ai-settings/', views.ai_settings_panel, name='ai_settings'),
#     path('api/ai/test-connection/', views.ai_test_connection_api, name='ai_test_connection'),
#     path('api/ai/save-settings/', views.ai_save_settings_api, name='ai_save_settings'),
#     path('api/ai/models/', views.ai_get_models_api, name='ai_get_models'),
#     path('api/ai/restart/', views.ai_restart_ollama_api, name='ai_restart_ollama'),

#     path('api/network/info/', views.get_network_info_api, name='network_info'),
#     path('api/network/save/', views.save_network_settings_api, name='save_network_settings'),
#     path('api/network/apply/', views.apply_network_settings_api, name='apply_network_settings'),


#     # ==================== آدرس‌های حذف ====================
#     path('delete-role/<int:role_id>/', views.delete_role_view, name='delete_role'),
#     path('delete-user/<int:user_id>/', views.delete_user_view, name='delete_user'),
#     path('delete-user-modal/<int:user_id>/', views.delete_user_modal_view, name='delete_user_modal'),
#     path('delete-role-modal/<int:role_id>/', views.delete_role_modal_view, name='delete_role_modal'),
#     path('bulk-delete-users/', views.bulk_delete_users_view, name='bulk_delete_users'),
#     path('bulk-delete-roles/', views.bulk_delete_roles_view, name='bulk_delete_roles'),




#     # ==================== آدرس‌های نوتیفیکیشن ====================
#     path('api/notifications/', views.get_notifications_api, name='get_notifications'),
#     path('api/notifications/<int:notification_id>/read/', views.mark_notification_read_api, name='mark_notification_read'),
#     path('api/notifications/read-all/', views.mark_all_notifications_read_api, name='mark_all_notifications_read'),
#     path('notifications/', views.notifications_panel_view, name='notifications_panel'),
#     path('file-analysis/<int:file_id>/', views.analyze_file_detail_view, name='file_analysis_detail'),
#     path('api/file-analyze/<int:file_id>/', views.analyze_file_manual_api, name='analyze_file_manual'),
#     path('api/alerts-count/', views.alerts_count_api, name='alerts_count_api'),

#     ############################

# ]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)







from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from core import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('api/upload/', views.upload_files_view, name='upload_files'),
    path('api/settings/', views.save_settings_view, name='save_settings'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('api/admin-action/', views.admin_action_view, name='admin_action'),
    path('super-admin/', views.super_admin_panel, name='super_admin_panel'),
    path('api/super-admin-action/', views.super_admin_action, name='super_admin_action'),
    path('api/users/', views.api_users, name='api_users'),
    path('api/send-files/', views.send_files_view, name='send_files'),
    path('api/download-file/<int:file_id>/', views.download_file_view, name='download_file'),
    path('api/delete-my-file/', views.delete_my_file_view, name='delete_my_file'),
    
    # AI و امنیت
    path('api/analyze-file/<int:file_id>/', views.analyze_file_with_ai, name='analyze_file_ai'),
    path('api/analyze-user/<int:user_id>/', views.analyze_user_view, name='analyze_user'),
    path('api/analyze-all-files/', views.analyze_all_files_view, name='analyze_all_files'),
    path('api/analyze-all-users/', views.analyze_all_users_view, name='analyze_all_users'),
    path('api/alerts/count/', views.alerts_count_view, name='alerts_count'),
    path('api/security-stats/', views.security_stats_view, name='security_stats'),
    path('api/my-permissions/', views.my_permissions_view, name='my_permissions'),
    
    # مدیریت فایل و هشدارها
    path('file-summary/<int:file_id>/', views.file_summary_view, name='file_summary'),
    path('security-alerts/', views.security_alerts_view, name='security_alerts'),
    path('resolve-alert/<int:alert_id>/', views.resolve_alert_view, name='resolve_alert'),
    path('login-logs/', views.login_logs_view, name='login_logs'),
    path('user-detail/<int:user_id>/', views.user_detail_view, name='user_detail'),
    
    # APIهای مدیریتی
    path('api/all-permissions/', views.get_all_permissions, name='all_permissions'),
    path('api/roles/', views.get_all_roles, name='api_roles'),
    path('api/role-permissions/<int:role_id>/', views.get_role_permissions, name='api_role_permissions'),
    path('api/save-role-permissions/', views.save_role_permissions, name='api_save_role_permissions'),
    path('api/create-role/', views.create_new_role, name='api_create_role'),
    path('api/users-list/', views.get_users_list, name='api_users_list'),
    path('api/set-password-policy/', views.set_password_policy, name='api_set_password_policy'),
    path('api/toggle-block/<int:user_id>/', views.toggle_block_user, name='api_toggle_block'),
    path('api/delete-user/<int:user_id>/', views.delete_user_by_id, name='api_delete_user'),
    
    # تحلیل شخصیت
    path('api/analyze-user-personality/<int:user_id>/', views.analyze_user_personality_view, name='analyze_user_personality'),
    
    # تنظیمات AI
    path('ai-settings/', views.ai_settings_panel, name='ai_settings'),
    path('api/ai/test-connection/', views.ai_test_connection_api, name='ai_test_connection'),
    path('api/ai/save-settings/', views.ai_save_settings_api, name='ai_save_settings'),
    path('api/ai/models/', views.ai_get_models_api, name='ai_get_models'),
    path('api/ai/restart/', views.ai_restart_ollama_api, name='ai_restart_ollama'),

    # شبکه
    path('api/network/info/', views.get_network_info_api, name='network_info'),
    path('api/network/save/', views.save_network_settings_api, name='save_network_settings'),
    path('api/network/apply/', views.apply_network_settings_api, name='apply_network_settings'),

    # حذف
    path('delete-role/<int:role_id>/', views.delete_role_view, name='delete_role'),
    path('delete-user/<int:user_id>/', views.delete_user_view, name='delete_user'),
    path('delete-user-modal/<int:user_id>/', views.delete_user_modal_view, name='delete_user_modal'),
    path('delete-role-modal/<int:role_id>/', views.delete_role_modal_view, name='delete_role_modal'),
    path('bulk-delete-users/', views.bulk_delete_users_view, name='bulk_delete_users'),
    path('bulk-delete-roles/', views.bulk_delete_roles_view, name='bulk_delete_roles'),

    # ==================== نوتیفیکیشن ====================
    path('api/notifications/', views.get_notifications_api, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read_api, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read_api, name='mark_all_notifications_read'),
    path('notifications/', views.notifications_panel_view, name='notifications_panel'),
    path('file-analysis/<int:file_id>/', views.analyze_file_detail_view, name='file_analysis_detail'),
    
    # ====== این فقط یک بار باشه ======
    path('api/file-analyze/<int:file_id>/', views.analyze_file_manual_api, name='analyze_file_manual'),
    
    path('api/alerts-count/', views.alerts_count_api, name='alerts_count_api'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)