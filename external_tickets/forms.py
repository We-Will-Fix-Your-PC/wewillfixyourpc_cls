from django import forms
from ckeditor_uploader.fields import RichTextUploadingFormField
import tickets.models


class TicketForm(forms.ModelForm):
    class Meta:
        model = tickets.models.Ticket
        fields = [
            'equipment', 'has_case', 'other_equipment', 'whats_it_doing'
        ]
        widgets = {
            'whats_it_doing': RichTextUploadingFormField(required=True),
        }
