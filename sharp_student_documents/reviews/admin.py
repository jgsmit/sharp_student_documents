from django.contrib import admin
from .models import FAQ, HelpArticle, Review, HelpCategory

# ---------------------------------
# FAQ Admin
# ---------------------------------
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order')
    list_editable = ('order',)
    ordering = ('order',)
    search_fields = ('question', 'answer')


# ---------------------------------
# HelpArticle Admin
# ---------------------------------
@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'published', 'order')
    list_editable = ('published', 'order')
    ordering = ('order',)
    search_fields = ('title', 'content')
    list_filter = ('published', 'category')


# ---------------------------------
# Review Admin
# ---------------------------------
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('document', 'reviewer', 'rating', 'comment', 'created_at')
    search_fields = ('document__title', 'reviewer__username', 'comment')
    list_filter = ('rating', 'created_at')
    readonly_fields = ('created_at',)


# ---------------------------------
# HelpCategory Admin
# ---------------------------------
@admin.register(HelpCategory)
class HelpCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name',)
