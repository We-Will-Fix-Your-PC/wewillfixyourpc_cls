from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField


class ItemCategory(models.Model):
    name = models.CharField(max_length=255, blank=False)

    class Meta:
        verbose_name_plural = "Item categories"

    def __str__(self):
        return self.name


class Item(models.Model):
    category = models.ForeignKey(ItemCategory, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False)
    condition = models.CharField(max_length=255, blank=False)
    price = models.DecimalField(decimal_places=2, max_digits=10, blank=False)
    description = RichTextUploadingField(blank=True, null=True)
    changes_made = RichTextUploadingField(blank=True, null=True)

    def __str__(self):
        return self.name


class ItemImage(models.Model):
    item = models.ForeignKey(Item, related_name='images', on_delete=models.CASCADE)
    image = models.FileField(blank=False)

    def __str__(self):
        return f"#{self.id}"
