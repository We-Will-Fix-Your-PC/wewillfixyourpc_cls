from django import forms
from ckeditor_uploader.fields import RichTextUploadingFormField
from . import models
from . import widgets


class TicketForm(forms.ModelForm):
    additional_labels = forms.IntegerField(min_value=0, initial=0)
    updater = forms.UUIDField(widget=widgets.AgentWidget())

    class Meta:
        model = models.Ticket
        fields = [
            'equipment', 'booked_by', 'assigned_to', 'current_os', 'wanted_os', 'status', 'quote',
            'has_charger', 'has_case', 'other_equipment', 'to_do_by', 'location', 'whats_it_doing', 'work_done'
        ]
        widgets = {
            'booked_by': widgets.AgentWidget(external_booker=True),
            'assigned_to': widgets.AgentWidget(),
            'updater': widgets.AgentWidget(),
            'to_do_by': forms.DateInput(),
            'whats_it_doing': RichTextUploadingFormField(required=True),
            'work_done': RichTextUploadingFormField(required=False)
        }


class JobForm(forms.ModelForm):
    class Meta:
        model = models.Job
        fields = [
            'assigned_to', 'title', 'description', 'to_do_by', 'completed'
        ]
        widgets = {
            'assigned_to': widgets.AgentWidget(),
            'description': RichTextUploadingFormField(required=False)
        }


EquipmentTypeFormSet = forms.modelformset_factory(models.EquipmentType, fields=('name',), can_delete=True)
StatusFormSet = forms.modelformset_factory(models.Status, fields=('name',), can_delete=True)
LocationFormSet = forms.modelformset_factory(models.Location, fields=('name', 'os_required'), can_delete=True)
OSTypeFormSet = forms.modelformset_factory(models.OSType, fields=('name',), can_delete=True)
TicketImageFormSet = forms.inlineformset_factory(
    models.Ticket, models.TicketImage, fields=('image',), can_delete=True, extra=1
)
