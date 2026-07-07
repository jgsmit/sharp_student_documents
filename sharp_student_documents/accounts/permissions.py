from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q

from .models import Role, UserRole
from documents.models import Document
from sales.models import Sale, Wallet
from education.models import StudyPlanner, LearningProgress
from withdrawals.models import WithdrawalRequest

def role_required(role_name):
    """Decorator to require specific role"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                if not request.user.has_role(role_name):
                    messages.error(request, f'You need {role_name} role to access this page.')
                    return redirect('login')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def has_any_role(role_names):
    """Decorator to require any of the specified roles"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                if not any(request.user.has_role(role) for role in role_names):
                    messages.error(request, 'You do not have permission to access this page.')
                    return redirect('login')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def admin_required(view_func):
    """Decorator to require admin role"""
    return role_required('Admin')(view_func)

def seller_required(view_func):
    """Decorator to require seller role"""
    return has_any_role(['Seller', 'Teacher', 'Admin'])(view_func)

def moderator_required(view_func):
    """Decorator to require moderator role"""
    return has_any_role(['Moderator', 'Admin'])(view_func)

def teacher_required(view_func):
    """Decorator to require teacher role"""
    return has_any_role(['Teacher', 'Admin'])(view_func)

def student_required(view_func):
    """Decorator to require student role"""
    return has_any_role(['Student', 'Teacher', 'Seller', 'Admin'])(view_func)

# Enhanced permission decorators
def can_upload_documents(view_func):
    """Check if user can upload documents"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.has_role(['Seller', 'Teacher', 'Admin']):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You need Seller, Teacher, or Admin role to upload documents.')
                return redirect('login')
        return wrapper
    return decorator

def can_manage_analytics(view_func):
    """Check if user can view analytics"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.has_role(['Admin', 'Moderator', 'Seller']):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You need Admin, Moderator, or Seller role to view analytics.')
                return redirect('login')
        return wrapper
    return decorator

def can_view_withdraw(view_func):
    """Check if user can withdraw funds"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.has_role(['Admin', 'Seller']):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You need Admin or Seller role to withdraw funds.')
                return redirect('login')
        return wrapper
    return decorator

def can_manage_security(view_func):
    """Check if user can access security features"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.has_role(['Admin', 'Moderator']):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You need Admin or Moderator role to access security features.')
                return redirect('login')
        return wrapper
    return decorator

def can_manage_education(view_func):
    """Check if user can access educational tools"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.has_role(['Student', 'Teacher', 'Seller', 'Admin']):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You need Student, Teacher, Seller, or Admin role to access educational tools.')
                return redirect('login')
        return wrapper
    return decorator

def can_review_content(view_func):
    """Check if user can review content"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.has_role(['Moderator', 'Admin']):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You need Moderator or Admin role to review content.')
                return redirect('login')
        return wrapper
    return decorator

# Template context processors
def user_roles(request):
    """Add user roles to template context"""
    if request.user.is_authenticated:
        return {
            'user_roles': request.user.get_all_roles(),
            'is_admin': request.user.is_admin,
            'is_moderator': request.user.is_moderator,
            'is_teacher': request.user.is_teacher,
            'is_student': request.user.is_student,
            'is_seller': request.user.is_seller,
        }
    return {}

def navigation_context(request):
    """Add navigation items based on user roles"""
    context = {}
    
    if request.user.is_authenticated:
        context['user'] = request.user
        
        # Navigation items based on roles
        nav_items = []
        
        # Basic navigation for all authenticated users
        nav_items.extend([
            ('My Purchases', 'my_purchases'),
            ('Profile', 'profile'),
            ('Logout', 'logout'),
        ])
        
        # Seller-specific navigation
        if request.user.is_seller or request.user.has_role(['Teacher', 'Admin']):
            nav_items.insert(0, ('Seller Dashboard', 'seller_dashboard'))
        
        # Admin-specific navigation
        if request.user.is_admin:
            nav_items.insert(0, ('Admin Panel', 'admin:index'))
        
        # Teacher-specific navigation
        if request.user.is_teacher:
            nav_items.insert(0, ('Teacher Dashboard', 'teacher_dashboard'))
        
        # Student-specific navigation
        if request.is_student:
            nav_items.insert(0, ('Study Planner', 'education:study_planner'))
        
        # Admin/Moderator navigation
        if request.user.is_admin or request.user.is_moderator:
            nav_items.insert(0, ('Analytics', 'documents:analytics'))
            nav_items.insert(1, ('Security', 'security:dashboard'))
        
        context['nav_items'] = nav_items
    
    return context
