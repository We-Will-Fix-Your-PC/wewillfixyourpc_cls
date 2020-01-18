from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from . import models
from . import forms


@login_required
@permission_required('sale.view_item', raise_exception=True)
def view_items(request):
    items = models.Item.objects.all()
    return render(request, "sale/items.html", {
        "items": items
    })


@login_required
@permission_required('sale.add_item', raise_exception=True)
def new_item(request):
    if request.method == 'POST':
        form = forms.ItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("sale:view_items")
    else:
        form = forms.ItemForm()

    return render(request, "sale/item_form.html", {
        "form": form,
        "title": "New item"
    })


@login_required
@permission_required('sale.change_item', raise_exception=True)
@permission_required('sale.add_itemimage', raise_exception=True)
@permission_required('sale.change_itemimage', raise_exception=True)
@permission_required('sale.delete_itemimage', raise_exception=True)
@permission_required('sale.view_itemimage', raise_exception=True)
def edit_item(request, item_id):
    item = get_object_or_404(models.Item, id=item_id)
    if request.method == 'POST':
        form = forms.ItemForm(request.POST, instance=item)
        images = forms.ItemImageFormSet(request.POST, files=request.FILES, prefix='images', instance=item)
        images.clean()
        if form.is_valid() and images.is_valid():
            form.save()
            images.save()
            return redirect("sale:view_items")
    else:
        form = forms.ItemForm(instance=item)
        images = forms.ItemImageFormSet(prefix='images', instance=item)

    return render(request, "sale/item_form.html", {
        "form": form,
        "images": images,
        "title": "Edit item"
    })


@login_required
@permission_required('sale.view_item', raise_exception=True)
@permission_required('sale.view_itemimage', raise_exception=True)
def view_item(request, item_id):
    item = get_object_or_404(models.Item, id=item_id)
    return render(request, "sale/item.html", {
        "item": item
    })


@login_required
@permission_required('sale.delete_item', raise_exception=True)
def delete_item(request, item_id):
    item = get_object_or_404(models.Item, id=item_id)
    item.delete()
    return redirect('sale:view_items')


@login_required
@permission_required('sale.change_itemcategory', raise_exception=True)
@permission_required('sale.add_itemcategory', raise_exception=True)
@permission_required('sale.delete_itemcategory', raise_exception=True)
@permission_required('sale.view_itemcategory', raise_exception=True)
def item_settings(request):
    if request.method == 'POST':
        categories = forms.ItemCategoryFormSet(request.POST, prefix='category')
        categories.clean()
        if categories.is_valid():
            categories.save()

            categories = forms.ItemCategoryFormSet(prefix='category')
    else:
        categories = forms.ItemCategoryFormSet(prefix='category')

    return render(request, 'sale/settings.html', {
        "categories": categories,
    })
