import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from .services.llm_service import llm_service
from .services.firewall_service import firewall
from .models import (
    FileActionLog, UploadedFile, UserSettings, UserProfile,
    PasswordPolicy, GroupLeader, LoginLog
)
from .permissions import has_permission, can_modify_user, check_permission
from .models import SystemPermission, UserPermission
import os
from django.db import models

from .models import (
    FileActionLog, UploadedFile, UserSettings, UserProfile,
    PasswordPolicy, GroupLeader, LoginLog, AINotification, AIThreatAlert
)


def get_or_create_settings(user):
    settings, created = UserSettings.objects.get_or_create(user=user)
    return settings


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        success = user is not None

        LoginLog.objects.create(
            user=user if user else None,
            ip_address=request.META.get('REMOTE_ADDR'),
            success=success
        )

        if user:
            login(request, user)
            role = 'superadmin' if user.is_superuser else 'admin' if user.is_staff else 'user'
            return JsonResponse({'success': True, 'uid': user.id, 'role': role})
        else:
            return JsonResponse({'success': False, 'msg': 'نام کاربری یا رمز عبور اشتباه است'})
    return render(request, 'login.html')


@login_required
def dashboard_view(request):
    settings = get_or_create_settings(request.user)
    my_files = UploadedFile.objects.filter(uploaded_by=request.user, is_deleted=False).order_by('-uploaded_at')
    return render(request, 'dashboard.html', {'settings': settings, 'my_files': my_files})


@csrf_exempt
@login_required
def upload_files_view(request):
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        folder_name = request.POST.get('folder_name', 'Unknown')
        uploaded_count = 0
        rejected_count = 0
        threats_found = []
        notifications_created = []

        for f in files:
            if f.name.lower().endswith('.exe'):
                rejected_count += 1
                continue

            # 1. ذخیره فایل
            uploaded_file = UploadedFile.objects.create(
                file=f,
                uploaded_by=request.user,
                folder_name=folder_name
            )
            uploaded_count += 1

            # 2. ====== تحلیل خودکار با AI ======
            try:
                from .services.file_analysis_service import file_analysis_service
                print(f"🔍 [AI] شروع تحلیل فایل: {f.name}")

                analysis_result = file_analysis_service.analyze_uploaded_file(uploaded_file)

                if analysis_result.get('success'):
                    notifications_created.append({
                        'file': f.name,
                        'threat_level': analysis_result.get('threat_level', 'info'),
                        'notification_id': analysis_result.get('notification').id if analysis_result.get(
                            'notification') else None
                    })

                    if analysis_result.get('threat_level') in ['warning', 'critical']:
                        threats_found.append({
                            "file": f.name,
                            "threat": analysis_result.get('threat_level', 'unknown'),
                            "severity": analysis_result.get('threat_level', 'low')
                        })
                    print(f"✅ [AI] تحلیل فایل {f.name} با موفقیت انجام شد - سطح: {analysis_result.get('threat_level')}")
                else:
                    print(f"❌ [AI] تحلیل فایل {f.name} ناموفق: {analysis_result.get('error')}")

            except Exception as e:
                print(f"❌ [AI] خطا در تحلیل فایل {f.name}: {e}")
                import traceback
                traceback.print_exc()
            # =================================

            # 3. اسکن توسط فایروال هوشمند (قبلی)
            try:
                scan_result = firewall.scan_file(uploaded_file)

                if scan_result.get("is_threat", False):
                    threats_found.append({
                        "file": f.name,
                        "threat": scan_result.get("threat_type", "unknown"),
                        "severity": scan_result.get("severity", "low")
                    })
            except Exception as e:
                print(f"⚠️ خطا در اسکن فایروال برای {f.name}: {e}")

        # پیام نهایی
        msg = f'{uploaded_count} فایل آپلود شد.'
        if rejected_count > 0:
            msg += f' {rejected_count} فایل EXE مجاز نبود.'

        if threats_found:
            msg += f' ⚠️ {len(threats_found)} فایل مشکوک شناسایی شد!'

        if notifications_created:
            msg += f' 📬 {len(notifications_created)} نوتیفیکیشن جدید برای ادمین‌ها ارسال شد.'

        return JsonResponse({
            'success': True,
            'msg': msg,
            'threats': threats_found,
            'notifications': notifications_created
        })

    return JsonResponse({'success': False, 'msg': 'خطا در آپلود'})


@csrf_exempt
@login_required
def save_settings_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        settings = get_or_create_settings(request.user)
        settings.font_size = int(data.get('font_size', 14))
        settings.menu_size = int(data.get('menu_size', 200))
        settings.button_size = int(data.get('button_size', 40))
        settings.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
def admin_panel_view(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    users = User.objects.all()
    history = UploadedFile.objects.filter(is_deleted=False).select_related('uploaded_by').order_by('-uploaded_at')
    all_roles = Group.objects.all()
    context = {
        'users': users,
        'history': history,
        'all_roles': all_roles,
    }
    return render(request, 'admin_panel.html', context)


@login_required
def super_admin_panel(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    policy, _ = PasswordPolicy.objects.get_or_create(pk=1)
    all_perms = Permission.objects.all()
    users = User.objects.all()
    all_roles = Group.objects.all()

    context = {
        'policy': policy,
        'all_perms': all_perms,
        'users': users,
        'all_roles': all_roles,
    }
    return render(request, 'super_admin_panel.html', context)


@csrf_exempt
@login_required
def admin_action_view(request):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'Unauthorized'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'msg': 'داده نامعتبر'}, status=400)

    action = data.get('action')

    # ایجاد کاربر جدید
    if action == 'create_user':
        if not has_permission(request.user, 'create_user'):
            return JsonResponse({'success': False, 'msg': 'شما دسترسی ایجاد کاربر ندارید'}, status=403)

        username = data.get('username')
        password = data.get('password')
        is_staff = data.get('is_staff', False)
        groups = data.get('groups', [])

        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'msg': 'نام کاربری تکراری است'})

        user = User.objects.create_user(username=username, password=password)
        user.is_staff = is_staff
        user.save()

        if groups:
            group_objs = Group.objects.filter(id__in=groups)
            user.groups.set(group_objs)

        UserProfile.objects.get_or_create(user=user)
        return JsonResponse({'success': True, 'msg': 'کاربر جدید ساخته شد'})

    # تغییر رمز عبور
    elif action == 'change_password':
        if not has_permission(request.user, 'change_password'):
            return JsonResponse({'success': False, 'msg': 'شما دسترسی تغییر رمز ندارید'}, status=403)

        target_user = get_object_or_404(User, id=data.get('user_id'))

        if target_user.id == request.user.id and not request.user.is_superuser:
            return JsonResponse(
                {'success': False, 'msg': 'نمی‌توانید رمز خودتان را تغییر دهید. از بخش پروفایل اقدام کنید.'},
                status=403)

        target_user.set_password(data.get('new_password'))
        target_user.save()
        return JsonResponse({'success': True, 'msg': 'رمز عبور تغییر کرد'})

    # مسدود کردن کاربر
    elif action == 'block_user':
        if not has_permission(request.user, 'block_user'):
            return JsonResponse({'success': False, 'msg': 'شما دسترسی مسدود کردن کاربر را ندارید'}, status=403)

        user_id = data.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'msg': 'شناسه کاربر نامعتبر'})

        if int(user_id) == request.user.id:
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید خودتان را مسدود کنید'}, status=403)

        user = get_object_or_404(User, id=user_id)

        if user.is_superuser and not request.user.is_superuser:
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید سوپر ادمین را مسدود کنید'}, status=403)

        user.is_active = False
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.is_blocked = True
        profile.blocked_at = timezone.now()
        profile.save()

        return JsonResponse({'success': True, 'msg': f'کاربر {user.username} مسدود شد'})

    # فعال کردن کاربر
    elif action == 'unblock_user':
        if not has_permission(request.user, 'block_user'):
            return JsonResponse({'success': False, 'msg': 'شما دسترسی فعال کردن کاربر را ندارید'}, status=403)

        user_id = data.get('user_id')
        user = get_object_or_404(User, id=user_id)

        if user.id == request.user.id:
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید وضعیت خودتان را تغییر دهید'}, status=403)

        user.is_active = True
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.is_blocked = False
        profile.blocked_at = None
        profile.save()

        return JsonResponse({'success': True, 'msg': f'کاربر {user.username} آزاد شد'})

    # حذف فایل
    elif action == 'delete_file':
        if not has_permission(request.user, 'delete_own_file') and not request.user.is_superuser:
            return JsonResponse({'success': False, 'msg': 'شما دسترسی حذف فایل را ندارید'}, status=403)

        file_id = data.get('file_id')
        uploaded_file = get_object_or_404(UploadedFile, id=file_id)

        if uploaded_file.uploaded_by != request.user and not request.user.is_staff:
            return JsonResponse({'success': False, 'msg': 'شما مالک این فایل نیستید'}, status=403)

        if uploaded_file.file:
            uploaded_file.file.delete()
        uploaded_file.delete()

        return JsonResponse({'success': True, 'msg': 'فایل حذف شد'})

    # ==================== اضافه کردن اکشن حذف کاربر ====================
    elif action == 'delete_user':
        if not request.user.is_superuser:
            return JsonResponse({'success': False, 'msg': 'فقط سوپرادمین می‌تواند کاربر حذف کند'}, status=403)

        user_id = data.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'msg': 'شناسه کاربر نامعتبر'})

        target_user = get_object_or_404(User, id=user_id)

        # جلوگیری از حذف خودش
        if target_user.id == request.user.id:
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید خودتان را حذف کنید'}, status=403)

        # جلوگیری از حذف آخرین سوپرادمین
        if target_user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید آخرین سوپرادمین را حذف کنید'}, status=403)

        username = target_user.username

        # حذف فایل‌های کاربر
        user_files = UploadedFile.objects.filter(uploaded_by=target_user)
        for file_obj in user_files:
            if file_obj.file:
                try:
                    file_obj.file.delete()
                except:
                    pass
            file_obj.delete()

        target_user.delete()

        return JsonResponse({'success': True, 'msg': f'کاربر {username} با موفقیت حذف شد'})

    # اختصاص نقش به کاربر
    elif action == 'assign_role':
        if not has_permission(request.user, 'assign_role'):
            return JsonResponse({'success': False, 'msg': 'شما دسترسی اختصاص نقش را ندارید'}, status=403)

        user_id = data.get('user_id')
        role_id = data.get('role_id')
        assign = data.get('assign', True)

        target_user = get_object_or_404(User, id=user_id)
        role = get_object_or_404(Group, id=role_id)

        if target_user.id == request.user.id and not request.user.is_superuser:
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید نقش خودتان را تغییر دهید'}, status=403)

        if assign:
            target_user.groups.add(role)
            msg = f'نقش {role.name} به کاربر {target_user.username} اضافه شد'
        else:
            target_user.groups.remove(role)
            msg = f'نقش {role.name} از کاربر {target_user.username} حذف شد'

        return JsonResponse({'success': True, 'msg': msg})

    return JsonResponse({'success': False, 'msg': 'Invalid action'})


@csrf_exempt
@login_required
def super_admin_action(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'msg': 'داده نامعتبر'}, status=400)

    action = data.get('action')

    if action == 'update_policy':
        policy = PasswordPolicy.objects.first()
        if policy:
            policy.min_password_length = data.get('min_length', 8)
            policy.require_uppercase = data.get('require_uppercase', True)
            policy.require_digit = data.get('require_digit', True)
            policy.require_special_char = data.get('require_special_char', False)
            policy.save()
        return JsonResponse({'success': True, 'msg': 'سیاست رمز عبور ذخیره شد.'})

    elif action == 'create_role_with_perms':
        role_name = data.get('role_name')
        perm_ids = data.get('permissions', [])
        leader_id = data.get('leader_id')

        if not role_name:
            return JsonResponse({'success': False, 'msg': 'نام نقش نمی‌تواند خالی باشد'})

        if Group.objects.filter(name=role_name).exists():
            return JsonResponse({'success': False, 'msg': 'نقش با این نام وجود دارد'})

        group = Group.objects.create(name=role_name)

        if perm_ids:
            permissions = Permission.objects.filter(id__in=perm_ids)
            group.permissions.set(permissions)

        if leader_id:
            try:
                leader = User.objects.get(id=leader_id)
                GroupLeader.objects.create(group=group, leader=leader)
            except User.DoesNotExist:
                pass

        return JsonResponse({'success': True, 'msg': f'نقش {role_name} ساخته شد.'})

    return JsonResponse({'success': False, 'msg': 'اکشن نامعتبر'})


@login_required
@require_http_methods(["GET"])
def api_users(request):
    users = User.objects.exclude(id=request.user.id).values('id', 'username', 'first_name', 'last_name')
    return JsonResponse(list(users), safe=False)


@csrf_exempt
@login_required
def send_files_view(request):
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        files = request.FILES.getlist('files')

        if not recipient_id or not files:
            return JsonResponse({'success': False, 'msg': 'اطلاعات ناقص'})

        try:
            recipient = User.objects.get(id=recipient_id)
            sent_count = 0
            for f in files:
                if f.name.lower().endswith('.exe'):
                    continue
                UploadedFile.objects.create(
                    file=f,
                    uploaded_by=request.user,
                    folder_name=f'ارسال شده به {recipient.username}',
                    sent_to_user=recipient
                )
                sent_count += 1
            return JsonResponse({'success': True, 'msg': f'{sent_count} فایل ارسال شد'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'msg': 'کاربر یافت نشد'})

    return JsonResponse({'success': False, 'msg': 'متد نامعتبر'})


@login_required
def download_file_view(request, file_id):
    try:
        uploaded_file = UploadedFile.objects.get(id=file_id, is_deleted=False)

        # بررسی دسترسی
        if uploaded_file.uploaded_by != request.user and not request.user.is_staff:
            return JsonResponse({'success': False, 'msg': 'دسترسی ندارید'}, status=403)

        # ====== ثبت دانلود با تحلیل AI ======
        from .services.action_analyzer import action_analyzer
        analysis_result = action_analyzer.analyze_action(
            user=request.user,
            action_type='download',
            file_obj=uploaded_file,
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return redirect(uploaded_file.file.url)

    except UploadedFile.DoesNotExist:
        return JsonResponse({'success': False, 'msg': 'فایل یافت نشد'}, status=404)


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')


@csrf_exempt
@login_required
def delete_my_file_view(request):
    """حذف فایل توسط خود کاربر"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            file_id = data.get('file_id')

            uploaded_file = UploadedFile.objects.get(id=file_id, uploaded_by=request.user)
            file_name = uploaded_file.file.name

            if uploaded_file.file:
                uploaded_file.file.delete()
            uploaded_file.delete()

            return JsonResponse({'success': True, 'msg': 'فایل با موفقیت حذف شد'})

        except UploadedFile.DoesNotExist:
            return JsonResponse({'success': False, 'msg': 'فایل یافت نشد'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'msg': str(e)}, status=400)

    return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)


@login_required
def login_logs_view(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    logs = LoginLog.objects.all().order_by('-login_time')
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_logs': logs.count(),
    }
    return render(request, 'login_logs.html', context)


@login_required
def user_detail_view(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')

    user = get_object_or_404(User, id=user_id)
    context = {
        'target_user': user,
    }
    return render(request, 'user_detail.html', context)


@login_required
def create_role_view(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    if request.method == 'POST':
        role_name = request.POST.get('role_name')
        if role_name and not Group.objects.filter(name=role_name).exists():
            Group.objects.create(name=role_name)
            messages.success(request, f'نقش {role_name} ایجاد شد')
        else:
            messages.error(request, 'خطا در ایجاد نقش')
        return redirect('super_admin_panel')

    return redirect('super_admin_panel')


@login_required
def file_summary_view(request, file_id):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    file_obj = get_object_or_404(UploadedFile, id=file_id)

    if request.method == 'POST':
        level = request.POST.get('level', 'summary')
        question = request.POST.get('question', '')

        content = firewall.extract_file_content(file_obj)

        try:
            if question:
                result = llm_service.answer_question_about_file(
                    content=content,
                    filename=file_obj.file.name,
                    question=question
                )
                return JsonResponse({'success': True, 'result': result, 'type': 'answer'})
            else:
                result = llm_service.summarize_file(
                    content=content,
                    filename=file_obj.file.name,
                    detail_level=level
                )
                return JsonResponse({'success': True, 'result': result, 'type': 'summary'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return render(request, 'file_summary.html', {'file': file_obj})


@login_required
def security_alerts_view(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    alerts = firewall.get_pending_alerts()

    from .models import AIThreatAlert
    stats = {
        'total': AIThreatAlert.objects.count(),
        'pending': AIThreatAlert.objects.filter(status='pending').count(),
        'critical': AIThreatAlert.objects.filter(severity='critical').count(),
        'high': AIThreatAlert.objects.filter(severity='high').count(),
    }

    return render(request, 'security_alerts.html', {'alerts': alerts, 'stats': stats})


@login_required
def resolve_alert_view(request, alert_id):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    from .models import AIThreatAlert
    alert = get_object_or_404(AIThreatAlert, id=alert_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'block':
            alert.file.is_deleted = True
            alert.file.save()
            alert.status = 'blocked'
        elif action == 'ignore':
            alert.status = 'ignored'
        elif action == 'review':
            alert.status = 'reviewed'

        alert.reviewed_by = request.user
        alert.reviewed_at = timezone.now()
        alert.save()

        messages.success(request, f'هشدار با موفقیت {dict(alert.STATUS_CHOICES).get(alert.status)} شد')
        return redirect('security_alerts')

    return render(request, 'resolve_alert.html', {'alert': alert})


@login_required
def alerts_count_view(request):
    if not request.user.is_staff:
        return JsonResponse({'count': 0})

    from .models import AIThreatAlert
    count = AIThreatAlert.objects.filter(status='pending').count()
    return JsonResponse({'count': count})


@login_required
def security_stats_view(request):
    if not request.user.is_staff:
        return JsonResponse({})

    from .models import AIThreatAlert
    pending = AIThreatAlert.objects.filter(status='pending').count()
    critical = AIThreatAlert.objects.filter(severity='critical').count()
    high = AIThreatAlert.objects.filter(severity='high').count()
    total = AIThreatAlert.objects.count()

    return JsonResponse({
        'pending_alerts': pending,
        'critical_alerts': critical,
        'high_alerts': high,
        'total_alerts': total,
        'recommendation': 'لطفاً هشدارهای بحرانی را فوری بررسی کنید' if critical > 0 else 'وضعیت امنیتی خوب است'
    })


@login_required
def analyze_file_with_ai(request, file_id):
    """تحلیل فایل با AI"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    file_obj = get_object_or_404(UploadedFile, id=file_id)

    # خواندن محتوای فایل
    content = ""
    file_path = file_obj.file.path
    ext = file_obj.file.name.split('.')[-1].lower() if '.' in file_obj.file.name else 'unknown'

    # استخراج محتوا بر اساس نوع فایل
    if ext == 'txt':
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()[:5000]
        except:
            content = "خطا در خواندن فایل"

    elif ext == 'pdf':
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                for page in pdf.pages[:5]:
                    content += page.extract_text() or ""
        except:
            content = "خطا در خواندن PDF"

    else:
        content = f"فایل {ext} - محتوا قابل نمایش نیست"

    # دریافت سطح خلاصه‌سازی
    action = request.POST.get('action', 'summarize')
    level = request.POST.get('level', 'summary')
    question = request.POST.get('question', '')

    try:
        if action == 'ask' and question:
            result = llm_service.answer_question_about_file(
                content=content,
                filename=file_obj.file.name,
                question=question
            )
            return JsonResponse({
                'success': True,
                'result': result,
                'file_name': file_obj.file.name
            })
        else:
            result = llm_service.summarize_file(
                content=content,
                filename=file_obj.file.name,
                detail_level=level
            )

            # بررسی تهدیدات (ساده)
            threat_status = {
                'severity': 'low',
                'threat_type': 'none'
            }

            # بررسی کلمات کلیدی مشکوک
            suspicious_keywords = ['password', 'hack', 'crack', 'malware', 'virus', 'phishing']
            content_lower = content.lower()
            for keyword in suspicious_keywords:
                if keyword in content_lower:
                    threat_status = {
                        'severity': 'high',
                        'threat_type': keyword
                    }
                    break

            return JsonResponse({
                'success': True,
                'result': result,
                'file_name': file_obj.file.name,
                'threat_status': threat_status
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def analyze_user_view(request, user_id):
    """تحلیل کاربر با AI"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    user = get_object_or_404(User, id=user_id)

    # جمع‌آوری اطلاعات کاربر
    user_files = UploadedFile.objects.filter(uploaded_by=user, is_deleted=False)
    file_types = {}
    for uf in user_files:
        ext = uf.file.name.split('.')[-1] if '.' in uf.file.name else 'unknown'
        file_types[ext] = file_types.get(ext, 0) + 1

    user_data = {
        'id': user.id,
        'username': user.username,
        'total_uploads': user_files.count(),
        'file_types': file_types,
        'is_staff': user.is_staff,
        'date_joined': user.date_joined.strftime('%Y/%m/%d') if user.date_joined else 'نامشخص'
    }

    # تحلیل با AI
    try:
        if llm_service is None:
            analysis = "⚠️ سرویس هوش مصنوعی در دسترس نیست. لطفاً اطمینان حاصل کنید که Ollama در حال اجراست."
        else:
            analysis = llm_service.analyze_user_behavior(user_data, [])

        return JsonResponse({
            'success': True,
            'analysis': analysis,
            'total_uploads': user_files.count(),
            'user': {
                'username': user.username,
                'id': user.id,
                'file_types': file_types
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f"خطا در تحلیل: {str(e)}"
        }, status=500)


@login_required
def analyze_all_files_view(request):
    """تحلیل همه فایل‌ها (آمار کلی)"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    total_files = UploadedFile.objects.filter(is_deleted=False).count()
    files_by_user = UploadedFile.objects.filter(is_deleted=False).values('uploaded_by__username').annotate(
        count=models.Count('id'))

    return JsonResponse({
        'success': True,
        'total_files': total_files,
        'files_by_user': list(files_by_user)
    })


@login_required
def analyze_all_users_view(request):
    """تحلیل همه کاربران"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    users = User.objects.all()
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    staff_users = users.filter(is_staff=True).count()

    return JsonResponse({
        'success': True,
        'total_users': total_users,
        'active_users': active_users,
        'staff_users': staff_users
    })


@login_required
def my_permissions_view(request):
    """دریافت دسترسی‌های کاربر جاری"""
    from .permissions import get_user_permissions_list

    permissions = get_user_permissions_list(request.user)

    return JsonResponse({
        'user_id': request.user.id,
        'username': request.user.username,
        'is_superuser': request.user.is_superuser,
        'is_staff': request.user.is_staff,
        'permissions': permissions
    })


@login_required
def get_all_roles(request):
    """دریافت تمام نقش‌ها (گروه‌ها)"""
    if not request.user.is_staff:
        return JsonResponse([], safe=False)

    roles = Group.objects.all().values('id', 'name')
    return JsonResponse(list(roles), safe=False)


@login_required
def get_all_permissions(request):
    """دریافت تمام دسترسی‌های واقعی Django"""
    if not request.user.is_staff:
        return JsonResponse([], safe=False)

    permissions = Permission.objects.all().values('id', 'name', 'codename')
    perm_list = []
    for p in permissions:
        name_fa = p['name']
        if 'Can add' in name_fa:
            name_fa = name_fa.replace('Can add', 'امکان افزودن')
        elif 'Can change' in name_fa:
            name_fa = name_fa.replace('Can change', 'امکان ویرایش')
        elif 'Can delete' in name_fa:
            name_fa = name_fa.replace('Can delete', 'امکان حذف')
        elif 'Can view' in name_fa:
            name_fa = name_fa.replace('Can view', 'امکان مشاهده')

        perm_list.append({
            'id': p['id'],
            'name': name_fa,
            'codename': p['codename']
        })

    return JsonResponse(perm_list, safe=False)


@login_required
def get_role_permissions(request, role_id):
    """دریافت دسترسی‌های یک نقش خاص"""
    if not request.user.is_staff:
        return JsonResponse([], safe=False)

    try:
        role = Group.objects.get(id=role_id)
        permissions = role.permissions.all().values_list('id', flat=True)
        return JsonResponse(list(permissions), safe=False)
    except Group.DoesNotExist:
        return JsonResponse([], safe=False)


@login_required
def save_role_permissions(request):
    """ذخیره دسترسی‌های یک نقش"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
        role_id = data.get('role_id')
        perm_ids = data.get('permissions', [])

        role = Group.objects.get(id=role_id)
        permissions = Permission.objects.filter(id__in=perm_ids)
        role.permissions.set(permissions)

        return JsonResponse({'success': True, 'msg': 'دسترسی‌ها با موفقیت ذخیره شد'})
    except Group.DoesNotExist:
        return JsonResponse({'success': False, 'msg': 'نقش یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'msg': str(e)}, status=400)


@login_required
def create_new_role(request):
    """ایجاد نقش جدید"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
        role_name = data.get('name', '').strip()

        if not role_name:
            return JsonResponse({'success': False, 'msg': 'نام نقش نمی‌تواند خالی باشد'})

        if Group.objects.filter(name=role_name).exists():
            return JsonResponse({'success': False, 'msg': 'نقش با این نام قبلاً وجود دارد'})

        group = Group.objects.create(name=role_name)

        return JsonResponse({'success': True, 'msg': f'نقش {role_name} با موفقیت ایجاد شد', 'role_id': group.id})
    except Exception as e:
        return JsonResponse({'success': False, 'msg': str(e)}, status=400)


@login_required
def get_users_list(request):
    """دریافت لیست کاربران برای پنل مدیریت"""
    if not request.user.is_staff:
        return JsonResponse([], safe=False)

    users = User.objects.all().values('id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff',
                                      'is_superuser')
    user_list = []
    for u in users:
        full_name = f"{u['first_name']} {u['last_name']}".strip() or u['username']
        user_list.append({
            'id': u['id'],
            'username': u['username'],
            'full_name': full_name,
            'email': u['email'],
            'is_active': u['is_active'],
            'is_staff': u['is_staff'],
            'is_superuser': u['is_superuser']
        })

    return JsonResponse(user_list, safe=False)


@login_required
def set_password_policy(request):
    """تنظیم سیاست رمز عبور"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
        min_length = data.get('min_length', 8)

        policy, created = PasswordPolicy.objects.get_or_create(pk=1)
        policy.min_password_length = min_length
        policy.save()

        return JsonResponse({'success': True, 'msg': 'سیاست رمز عبور ذخیره شد'})
    except Exception as e:
        return JsonResponse({'success': False, 'msg': str(e)}, status=400)


@login_required
def toggle_block_user(request, user_id):
    """تغییر وضعیت مسدودیت کاربر"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        target_user = User.objects.get(id=user_id)

        if target_user.id == request.user.id:
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید خودتان را مسدود کنید'}, status=403)

        target_user.is_active = not target_user.is_active
        target_user.save()

        profile, _ = UserProfile.objects.get_or_create(user=target_user)
        profile.is_blocked = not target_user.is_active
        profile.blocked_at = timezone.now() if profile.is_blocked else None
        profile.save()

        status = 'مسدود' if not target_user.is_active else 'فعال'
        return JsonResponse({'success': True, 'msg': f'کاربر {status} شد'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'msg': 'کاربر یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'msg': str(e)}, status=400)


@login_required
def delete_user_by_id(request, user_id):
    """حذف کاربر توسط ادمین"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        target_user = User.objects.get(id=user_id)

        if target_user.id == request.user.id:
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید خودتان را حذف کنید'}, status=403)

        username = target_user.username
        target_user.delete()

        return JsonResponse({'success': True, 'msg': f'کاربر {username} با موفقیت حذف شد'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'msg': 'کاربر یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'msg': str(e)}, status=400)


from .services.file_reader import FileReader


@login_required
def analyze_user_personality_view(request, user_id):
    """تحلیل شخصیت کاربر با AI - نمایش در صفحه"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    user = get_object_or_404(User, id=user_id)

    user_files = UploadedFile.objects.filter(uploaded_by=user, is_deleted=False).order_by('-uploaded_at')[:20]

    all_content = []
    file_types = {}
    suspicious_files = []

    for uf in user_files:
        try:
            file_info = FileReader.read_file(uf.file)
            ext = file_info['extension']
            file_types[ext] = file_types.get(ext, 0) + 1

            if file_info['content']:
                all_content.append(f"\n\n--- فایل: {uf.file.name} ---\n{file_info['content'][:2000]}")

            if ext in ['.exe', '.jar', '.bat', '.ps1', '.sh']:
                suspicious_files.append(uf.file.name)

        except Exception as e:
            all_content.append(f"\n\n--- فایل: {uf.file.name} (خطا در خواندن: {e}) ---")

    user_data = {
        'username': user.username,
        'total_uploads': user_files.count(),
        'file_types': file_types,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.strftime('%Y/%m/%d') if user.date_joined else 'نامشخص'
    }

    try:
        if llm_service is None:
            analysis = "⚠️ سرویس هوش مصنوعی در دسترس نیست. لطفاً اطمینان حاصل کنید که Ollama در حال اجراست."
        else:
            analysis = llm_service.analyze_user_personality(
                user_data,
                "\n".join(all_content)[:8000]
            )

        return JsonResponse({
            'success': True,
            'analysis': analysis,
            'stats': {
                'total_files': user_files.count(),
                'file_types': file_types,
                'suspicious_files': suspicious_files
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f"خطا در تحلیل: {str(e)}"
        }, status=500)


# ==================== تنظیمات هوش مصنوعی و سیستم ====================
from .models import AISettings, SystemSettings
from .services.ai_manager import ai_manager
import socket
import subprocess
import platform
import re
import psutil


@login_required
def ai_settings_panel(request):
    """پنل تنظیمات هوش مصنوعی و سیستم"""
    if not request.user.is_staff:
        messages.error(request, "شما دسترسی به این صفحه را ندارید!")
        return redirect('dashboard')

    ai_settings = AISettings.get_settings()
    system_settings = SystemSettings.get_settings()

    context = {
        'ai_settings': ai_settings,
        'system_settings': system_settings,
        'is_superuser': request.user.is_superuser
    }
    return render(request, 'ai_settings.html', context)


@csrf_exempt
@login_required
def ai_test_connection_api(request):
    """API تست اتصال به Ollama"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
        host = data.get('host')
        port = data.get('port')
        model = data.get('model')

        result = ai_manager.test_connection(host, port, model)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@csrf_exempt
@login_required
def ai_save_settings_api(request):
    """API ذخیره تنظیمات AI"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
        result = ai_manager.save_settings(data)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def ai_get_models_api(request):
    """API دریافت لیست مدل‌های موجود"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'models': []}, status=403)

    host = request.GET.get('host')
    port = request.GET.get('port')

    result = ai_manager.get_available_models(host, port)
    return JsonResponse(result)


@login_required
def ai_restart_ollama_api(request):
    """API ریستارت سرویس Ollama (فقط سوپرادمین)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'دسترسی غیرمجاز'}, status=403)

    try:
        import subprocess
        result = subprocess.run(['ollama', 'serve', '--restart'], capture_output=True, text=True)
        return JsonResponse({
            'success': True,
            'message': 'درخواست ریستارت ارسال شد',
            'output': result.stdout
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)



def get_network_info():
    """دریافت اطلاعات شبکه و سیستم (ویندوز)"""
    info = {
        'hostname': socket.gethostname(),
        'ip_address': '',
        'subnet_mask': '',
        'default_gateway': '',
        'primary_dns': '',
        'secondary_dns': '',
        'mac_address': '',
        'os': platform.system(),
        'os_version': platform.version(),
        'os_release': platform.release(),
        'python_version': platform.python_version(),
        'processor': platform.processor() or 'نامشخص',
        'ram_total': '',
        'ram_available': '',
    }

    try:
        if platform.system() == 'Windows':
            result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True, encoding='cp1256',
                                    errors='ignore')
            output = result.stdout

            ip_pattern = r'IPv4 Address[.\s]*: ([\d.]+)'
            subnet_pattern = r'Subnet Mask[.\s]*: ([\d.]+)'
            gateway_pattern = r'Default Gateway[.\s]*: ([\d.]+)'
            dns_pattern = r'DNS Servers[.\s]*: ([\d.]+)'
            mac_pattern = r'Physical Address[.\s]*: ([\w-]+)'

            ip_matches = re.findall(ip_pattern, output)
            for ip in ip_matches:
                if ip != '127.0.0.1' and ip != '0.0.0.0':
                    info['ip_address'] = ip
                    break

            subnet_match = re.search(subnet_pattern, output)
            gateway_match = re.search(gateway_pattern, output)
            dns_matches = re.findall(dns_pattern, output)
            mac_match = re.search(mac_pattern, output)

            if subnet_match:
                info['subnet_mask'] = subnet_match.group(1)
            if gateway_match and gateway_match.group(1) != '' and gateway_match.group(1) != '0.0.0.0':
                info['default_gateway'] = gateway_match.group(1)
            if dns_matches:
                valid_dns = [d for d in dns_matches if d != '0.0.0.0']
                if valid_dns:
                    info['primary_dns'] = valid_dns[0] if len(valid_dns) > 0 else ''
                    info['secondary_dns'] = valid_dns[1] if len(valid_dns) > 1 else ''
            if mac_match:
                info['mac_address'] = mac_match.group(1)

        elif platform.system() in ['Linux', 'Darwin']:
            result = subprocess.run(['ifconfig'], capture_output=True, text=True, errors='ignore')
            output = result.stdout

            ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
            if ip_match:
                info['ip_address'] = ip_match.group(1)

            result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True, errors='ignore')
            gateway_match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', result.stdout)
            if gateway_match:
                info['default_gateway'] = gateway_match.group(1)

            try:
                with open('/etc/resolv.conf', 'r') as f:
                    dns_content = f.read()
                    dns_matches = re.findall(r'nameserver (\d+\.\d+\.\d+\.\d+)', dns_content)
                    if dns_matches:
                        info['primary_dns'] = dns_matches[0] if len(dns_matches) > 0 else ''
                        info['secondary_dns'] = dns_matches[1] if len(dns_matches) > 1 else ''
            except:
                pass

    except Exception as e:
        print(f"Error getting network info: {e}")

    try:
        mem = psutil.virtual_memory()
        info['ram_total'] = f"{mem.total / (1024 ** 3):.1f} GB"
        info['ram_available'] = f"{mem.available / (1024 ** 3):.1f} GB"
    except:
        info['ram_total'] = 'نامشخص'
        info['ram_available'] = 'نامشخص'

    return info


@login_required
def get_network_info_api(request):
    """API دریافت اطلاعات شبکه"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'دسترسی غیرمجاز'}, status=403)

    info = get_network_info()
    return JsonResponse({'success': True, 'network_info': info})


@login_required
def save_network_settings_api(request):
    """API ذخیره تنظیمات شبکه"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
        settings = SystemSettings.get_settings()

        settings.server_ip = data.get('ip_address', settings.server_ip)
        settings.server_port = int(data.get('port', settings.server_port))
        settings.allow_remote_access = data.get('allow_remote_access', False)
        settings.save()

        return JsonResponse({
            'success': True,
            'message': 'تنظیمات شبکه با موفقیت ذخیره شد'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def apply_network_settings_api(request):
    """API اعمال تنظیمات شبکه در سیستم (فقط ویندوز)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'متد نامعتبر'}, status=405)

    if platform.system() != 'Windows':
        return JsonResponse({'success': False, 'message': 'این قابلیت فقط در ویندوز پشتیبانی می‌شود'}, status=400)

    try:
        data = json.loads(request.body)
        settings = SystemSettings.get_settings()

        interface_name = "Wi-Fi"
        ip = data.get('ip_address', settings.server_ip)
        subnet = data.get('subnet_mask', '255.255.255.0')
        gateway = data.get('default_gateway', '')
        dns1 = data.get('primary_dns', '8.8.8.8')
        dns2 = data.get('secondary_dns', '8.8.4.4')

        if ip and subnet:
            commands = [
                f'netsh interface ip set address "{interface_name}" static {ip} {subnet} {gateway}',
                f'netsh interface ip set dns "{interface_name}" static {dns1}',
                f'netsh interface ip add dns "{interface_name}" {dns2} index=2'
            ]

            results = []
            for cmd in commands:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                results.append({
                    'command': cmd,
                    'output': result.stdout,
                    'error': result.stderr
                })

            return JsonResponse({
                'success': True,
                'message': 'تنظیمات شبکه با موفقیت اعمال شد',
                'results': results
            })
        else:
            return JsonResponse({'success': False, 'message': 'IP و Subnet نمی‌توانند خالی باشند'}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


# ==================== حذف نقش و کاربر ====================

@login_required
def delete_role_view(request, role_id):
    """حذف نقش (فقط سوپرادمین)"""
    if not request.user.is_superuser:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)
        messages.error(request, 'شما دسترسی حذف نقش را ندارید!')
        return redirect('super_admin_panel')

    role = get_object_or_404(Group, id=role_id)

    protected_roles = ['admin', 'superadmin', 'user']
    if role.name.lower() in protected_roles:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'msg': f'نقش {role.name} قابل حذف نیست'}, status=400)
        messages.error(request, f'نقش {role.name} قابل حذف نیست!')
        return redirect('super_admin_panel')

    role_name = role.name
    role.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'msg': f'نقش {role_name} با موفقیت حذف شد'})

    messages.success(request, f'نقش {role_name} با موفقیت حذف شد')
    return redirect('super_admin_panel')


@login_required
def delete_user_view(request, user_id):
    """حذف کاربر (فقط سوپرادمین)"""
    if not request.user.is_superuser:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)
        messages.error(request, 'شما دسترسی حذف کاربر را ندارید!')
        return redirect('dashboard')

    target_user = get_object_or_404(User, id=user_id)

    if target_user.id == request.user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید خودتان را حذف کنید'}, status=400)
        messages.error(request, 'نمی‌توانید خودتان را حذف کنید!')
        return redirect('super_admin_panel')

    if target_user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید آخرین سوپرادمین را حذف کنید'}, status=400)
        messages.error(request, 'نمی‌توانید آخرین سوپرادمین را حذف کنید!')
        return redirect('super_admin_panel')

    username = target_user.username

    user_files = UploadedFile.objects.filter(uploaded_by=target_user)
    for file_obj in user_files:
        if file_obj.file:
            try:
                file_obj.file.delete()
            except:
                pass
        file_obj.delete()

    target_user.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'msg': f'کاربر {username} با موفقیت حذف شد'})

    messages.success(request, f'کاربر {username} با موفقیت حذف شد')
    return redirect('super_admin_panel')


@login_required
def delete_user_modal_view(request, user_id):
    """نمایش مودال تایید حذف کاربر"""
    if not request.user.is_superuser:
        return redirect('dashboard')

    target_user = get_object_or_404(User, id=user_id)
    context = {
        'target_user': target_user,
    }
    return render(request, 'includes/delete_user_modal.html', context)


@login_required
def delete_role_modal_view(request, role_id):
    """نمایش مودال تایید حذف نقش"""
    if not request.user.is_superuser:
        return redirect('dashboard')

    role = get_object_or_404(Group, id=role_id)
    context = {
        'role': role,
    }
    return render(request, 'includes/delete_role_modal.html', context)


@login_required
def bulk_delete_users_view(request):
    """حذف چند کاربر به صورت یکجا (فقط سوپرادمین)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])

        if not user_ids:
            return JsonResponse({'success': False, 'msg': 'هیچ کاربری انتخاب نشده است'})

        if str(request.user.id) in user_ids:
            return JsonResponse({'success': False, 'msg': 'نمی‌توانید خودتان را حذف کنید'})

        superadmins = User.objects.filter(is_superuser=True)
        if len(superadmins) <= 1:
            for uid in user_ids:
                user = User.objects.filter(id=uid, is_superuser=True).first()
                if user:
                    return JsonResponse({'success': False, 'msg': 'نمی‌توانید آخرین سوپرادمین را حذف کنید'})

        deleted_count = 0
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                if user.id != request.user.id:
                    user_files = UploadedFile.objects.filter(uploaded_by=user)
                    for file_obj in user_files:
                        if file_obj.file:
                            try:
                                file_obj.file.delete()
                            except:
                                pass
                        file_obj.delete()
                    user.delete()
                    deleted_count += 1
            except User.DoesNotExist:
                continue

        return JsonResponse({
            'success': True,
            'msg': f'{deleted_count} کاربر با موفقیت حذف شدند'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'msg': str(e)}, status=400)


@login_required
def bulk_delete_roles_view(request):
    """حذف چند نقش به صورت یکجا (فقط سوپرادمین)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        data = json.loads(request.body)
        role_ids = data.get('role_ids', [])

        if not role_ids:
            return JsonResponse({'success': False, 'msg': 'هیچ نقشی انتخاب نشده است'})

        protected_roles = ['admin', 'superadmin', 'user']
        deleted_count = 0

        for role_id in role_ids:
            try:
                role = Group.objects.get(id=role_id)
                if role.name.lower() not in protected_roles:
                    role.delete()
                    deleted_count += 1
            except Group.DoesNotExist:
                continue

        return JsonResponse({
            'success': True,
            'msg': f'{deleted_count} نقش با موفقیت حذف شدند'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'msg': str(e)}, status=400)


# ==================== API نوتیفیکیشن‌ها ====================

@login_required
def get_notifications_api(request):
    """دریافت نوتیفیکیشن‌های کاربر - فقط برای ادمین‌ها"""
    if not request.user.is_staff:
        return JsonResponse({'notifications': [], 'unread_count': 0, 'total': 0}, status=403)

    try:
        notifications = AINotification.objects.filter(target_users=request.user)

        unread_count = notifications.filter(status='unread').count()

        notifications_list = []
        for notif in notifications[:50]:
            file_name = None
            if notif.file:
                try:
                    if hasattr(notif.file, 'file') and notif.file.file:
                        file_name = notif.file.file.name
                    else:
                        file_name = str(notif.file)
                except:
                    file_name = 'فایل نامشخص'

            user_name = None
            if notif.user:
                try:
                    user_name = notif.user.username
                except:
                    user_name = 'کاربر نامشخص'

            notifications_list.append({
                'id': notif.id,
                'title': notif.title or 'بدون عنوان',
                'message': notif.message[:200] if notif.message else '',
                'severity': notif.severity or 'info',
                'status': notif.status or 'unread',
                'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M') if notif.created_at else '',
                'file_name': file_name,
                'user_name': user_name
            })

        return JsonResponse({
            'notifications': notifications_list,
            'unread_count': unread_count,
            'total': notifications.count()
        })

    except Exception as e:
        print(f"Error in get_notifications_api: {e}")
        return JsonResponse({
            'notifications': [],
            'unread_count': 0,
            'total': 0,
            'error': str(e)
        }, status=500)


@login_required
def mark_notification_read_api(request, notification_id):
    """علامت‌گذاری نوتیفیکیشن به عنوان خوانده شده"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    try:
        notification = AINotification.objects.get(id=notification_id, target_users=request.user)
        notification.status = 'read'
        notification.read_at = timezone.now()
        notification.save()
        return JsonResponse({'success': True, 'msg': 'نوتیفیکیشن خوانده شد'})
    except AINotification.DoesNotExist:
        return JsonResponse({'success': False, 'msg': 'نوتیفیکیشن یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'msg': str(e)}, status=500)


@login_required
def mark_all_notifications_read_api(request):
    """علامت‌گذاری همه نوتیفیکیشن‌ها به عنوان خوانده شده"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    try:
        notifications = AINotification.objects.filter(target_users=request.user, status='unread')
        count = notifications.count()

        for notif in notifications:
            notif.status = 'read'
            notif.read_at = timezone.now()
            notif.save()

        return JsonResponse({'success': True, 'msg': f'{count} نوتیفیکیشن خوانده شد'})
    except Exception as e:
        return JsonResponse({'success': False, 'msg': str(e)}, status=500)


@login_required
def notifications_panel_view(request):
    """صفحه نمایش نوتیفیکیشن‌ها - فقط برای ادمین‌ها"""
    if not request.user.is_staff:
        return redirect('dashboard')

    try:
        notifications = AINotification.objects.filter(target_users=request.user).order_by('-created_at')
        paginator = Paginator(notifications, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'total_count': notifications.count(),
            'unread_count': notifications.filter(status='unread').count(),
        }
        return render(request, 'notifications_panel.html', context)
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری نوتیفیکیشن‌ها: {str(e)}')
        return redirect('dashboard')


@login_required
def alerts_count_api(request):
    """API دریافت تعداد هشدارهای در انتظار"""
    if not request.user.is_staff:
        return JsonResponse({'count': 0})

    try:
        count = AIThreatAlert.objects.filter(status='pending').count()
        return JsonResponse({'count': count})
    except Exception as e:
        print(f"Error in alerts_count_api: {e}")
        return JsonResponse({'count': 0})


# ==================== توابع تحلیل فایل و نوتیفیکیشن ====================

@login_required
def analyze_file_detail_view(request, file_id):
    """نمایش تحلیل دقیق یک فایل"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    try:
        file_obj = get_object_or_404(UploadedFile, id=file_id, is_deleted=False)

        analysis = "تحلیلی برای این فایل ثبت نشده است"
        try:
            alert = AIThreatAlert.objects.filter(file=file_obj).first()
            if alert:
                analysis = alert.description
        except:
            pass

        context = {
            'file': file_obj,
            'analysis': analysis,
            'user': file_obj.uploaded_by,
        }
        return render(request, 'file_analysis_detail.html', context)

    except Exception as e:
        messages.error(request, f'خطا در بارگذاری تحلیل فایل: {str(e)}')
        return redirect('dashboard')


# @login_required
# @csrf_exempt
# def analyze_file_manual_api(request, file_id):
#     """تحلیل دستی فایل با AI (درخواست جدید)"""
#     if not request.user.is_staff:
#         return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

#     if request.method != 'POST':
#         return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

#     try:
#         file_obj = get_object_or_404(UploadedFile, id=file_id, is_deleted=False)

#         from .services.file_reader import FileReader

#         try:
#             file_info = FileReader.read_file(file_obj.file)
#             content = file_info.get('content', '')
#         except Exception as e:
#             content = f"خطا در خواندن فایل: {str(e)}"

#         if not llm_service or not llm_service.is_available:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'سرویس AI در دسترس نیست. لطفاً Ollama را راه‌اندازی کنید.'
#             }, status=503)

#         prompt = f"""
#         فایل "{file_obj.file.name}" را تحلیل کن و گزارش زیر را بنویس:

#         1. موضوع اصلی فایل چیست؟
#         2. آیا محتوای مشکوک یا خطرناکی دارد؟ (بله/خیر)
#         3. چه نوع اطلاعاتی در فایل وجود دارد؟ (شخصی/حساس/عمومی/فنی/مالی)
#         4. سطح ریسک فایل: (کم/متوسط/بالا/بحرانی)
#         5. خلاصه محتوا (۲-۳ خط):

#         محتوا:
#         {content[:3000] if content else 'فایل غیرقابل خواندن است'}

#         پاسخ:
#         """

#         analysis = llm_service._call_llm_stream(prompt)

#         severity = 'low'
#         if 'بحرانی' in analysis:
#             severity = 'critical'
#         elif 'بالا' in analysis:
#             severity = 'high'
#         elif 'متوسط' in analysis:
#             severity = 'medium'

#         AIThreatAlert.objects.create(
#             file=file_obj,
#             threat_type='manual_analysis',
#             severity=severity,
#             description=analysis[:500],
#             recommended_action='review' if severity in ['high', 'critical'] else 'none',
#             ai_raw_response=analysis,
#             status='reviewed'
#         )

#         return JsonResponse({
#             'success': True,
#             'analysis': analysis,
#             'threat_level': severity
#         })

#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)


@login_required
@csrf_exempt
def analyze_file_manual_api(request, file_id):
    """تحلیل دستی فایل با AI - با timeout بیشتر"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'msg': 'متد نامعتبر'}, status=405)

    try:
        file_obj = get_object_or_404(UploadedFile, id=file_id, is_deleted=False)

        from .services.file_reader import FileReader

        # خواندن محتوای فایل
        content = ""
        try:
            file_info = FileReader.read_file(file_obj.file)
            content = file_info.get('content', '')
        except Exception as e:
            content = f"خطا در خواندن فایل: {str(e)}"

        if not llm_service or not llm_service.is_available:
            return JsonResponse({
                'success': False,
                'error': 'سرویس AI در دسترس نیست. لطفاً Ollama را راه‌اندازی کنید.'
            }, status=503)

        # پرامپت کوتاه‌تر برای سرعت بیشتر
        prompt = f"""
        تحلیل فایل "{file_obj.file.name}":

        محتوا (خلاصه):
        {content[:1500]}

        پاسخ دهید:
        1. موضوع اصلی:
        2. آیا خطرناک است؟ (بله/خیر/مشکوک)
        3. سطح ریسک: (کم/متوسط/بالا/بحرانی)
        4. توصیه:
        """

        print(f"🤖 شروع تحلیل فایل: {file_obj.file.name}")

        # ارسال با timeout 120 ثانیه
        analysis = llm_service._call_llm_stream(prompt)

        # تشخیص سطح تهدید
        threat_level = 'low'
        analysis_lower = analysis.lower()
        if any(word in analysis_lower for word in ['بحرانی', 'خطرناک', 'ویروس', 'بدافزار']):
            threat_level = 'critical'
        elif any(word in analysis_lower for word in ['بالا', 'مشکوک', 'غیرمجاز']):
            threat_level = 'high'
        elif any(word in analysis_lower for word in ['متوسط']):
            threat_level = 'medium'
        elif 'مشکوک' in analysis_lower:
            threat_level = 'warning'

        # ذخیره نتیجه
        severity_map = {
            'low': 'low',
            'medium': 'medium',
            'high': 'high',
            'warning': 'medium',
            'critical': 'critical'
        }

        AIThreatAlert.objects.create(
            file=file_obj,
            threat_type='manual_analysis',
            severity=severity_map.get(threat_level, 'low'),
            description=analysis[:500],
            recommended_action='review' if threat_level in ['high', 'critical', 'warning'] else 'none',
            ai_raw_response=analysis,
            status='reviewed',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )

        return JsonResponse({
            'success': True,
            'analysis': analysis,
            'threat_level': threat_level
        })





    except Exception as e:
        print(f"❌ خطا در تحلیل: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def action_log_view(request):
    """نمایش لاگ عملیات با تحلیل AI - فقط برای ادمین‌ها"""
    if not request.user.is_staff:
        return redirect('dashboard')

    try:
        logs = FileActionLog.objects.all().order_by('-action_time')
        paginator = Paginator(logs, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'total_logs': logs.count(),
        }
        return render(request, 'action_log.html', context)
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری لاگ: {str(e)}')
        return redirect('dashboard')


@login_required
def action_log_detail_api(request, log_id):
    """API دریافت جزئیات یک لاگ عملیات"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    try:
        log = FileActionLog.objects.get(id=log_id)
        return JsonResponse({
            'success': True,
            'analysis': log.ai_analysis or 'تحلیلی برای این عملیات ثبت نشده است',
            'summary': log.ai_summary or '',
            'action': log.action,
            'file_name': log.file_name,
            'user': log.user.username if log.user else 'نامشخص',
            'created_at': log.action_time.strftime('%Y-%m-%d %H:%M')
        })
    except FileActionLog.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'لاگ یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def resolve_alert_view(request, alert_id):
    """رسیدگی به هشدار امنیتی"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'msg': 'دسترسی غیرمجاز'}, status=403)

    alert = get_object_or_404(AIThreatAlert, id=alert_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'block':
            alert.file.is_deleted = True
            alert.file.save()
            alert.status = 'blocked'
        elif action == 'ignore':
            alert.status = 'ignored'
        elif action == 'review':
            alert.status = 'reviewed'

        alert.reviewed_by = request.user
        alert.reviewed_at = timezone.now()
        alert.save()

        messages.success(request, f'هشدار با موفقیت {dict(alert.STATUS_CHOICES).get(alert.status)} شد')
        return redirect('security_alerts')

    return render(request, 'resolve_alert.html', {'alert': alert})


