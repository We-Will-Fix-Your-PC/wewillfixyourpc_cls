from django import forms
from ckeditor_uploader.fields import RichTextUploadingFormField
from . import models


class ItemForm(forms.ModelForm):
    class Meta:
        model = models.Item
        fields = [
            'category', 'name', 'price', 'description'
        ]
        widgets = {
            'description': RichTextUploadingFormField(required=False)
        }


ItemCategoryFormSet = forms.modelformset_factory(models.ItemCategory, fields=('name',), can_delete=True)
ItemImageFormSet = forms.inlineformset_factory(
    models.Item, models.ItemImage, fields=('image',), can_delete=True, extra=1
)
