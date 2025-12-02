from apps.product.models import Category
from .models import Config


def categories(request):
    """Make categories available to all templates"""
    return {
        'all_categories': Category.objects.all().order_by('name')
    }


def config(request):
    """Make config available to all templates"""
    return {
        'config': Config.objects.first()
    }
