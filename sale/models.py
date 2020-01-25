from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField


class ItemCategory(models.Model):
    name = models.CharField(max_length=255, blank=False)
    google_category = models.CharField(max_length=255, blank=False)

    class Meta:
        verbose_name_plural = "Item categories"

    def __str__(self):
        return self.name


class Item(models.Model):
    CONDITIONS = (
        ('new', 'New'),
        ('refurbished', 'Refurbished'),
        ('used', 'Used'),
        ('used_fair', 'Used - Fair'),
        ('used_good', 'Used - Good'),
        ('used_like_new', 'Used - Like ew')
    )

    category = models.ForeignKey(ItemCategory, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False)
    brand = models.CharField(max_length=255, blank=False)
    condition = models.CharField(max_length=30, blank=False, choices=CONDITIONS)
    price = models.DecimalField(decimal_places=2, max_digits=10, blank=False)
    description = models.TextField()
    available = models.BooleanField()
    changes_made = RichTextUploadingField(blank=True, null=True)

    def __str__(self):
        return self.name


class ItemImage(models.Model):
    item = models.ForeignKey(Item, related_name='images', on_delete=models.CASCADE)
    image = models.FileField(blank=False)

    def __str__(self):
        return f"#{self.id}"
