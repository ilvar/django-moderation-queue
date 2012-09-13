from django.contrib import admin, messages
from django.forms.models import ModelForm
from django.contrib.contenttypes.models import ContentType
from django.core import urlresolvers
import django

from moderation.models import Changeset, MODERATION_STATUS_PENDING, MODERATION_STATUS_REJECTED, MODERATION_STATUS_APPROVED

from django.utils.translation import ugettext as _
from moderation.forms import BaseModeratedObjectForm
from moderation.diff import get_changes_between_models, calculate_full_diff


def approve_objects(modeladmin, request, queryset):
    for obj in queryset:
        obj.approve(user=request.user, reason='')

approve_objects.short_description = "Approve selected moderated objects"


def reject_objects(modeladmin, request, queryset):
    for obj in queryset:
        obj.reject(user=request.user, reason='')

reject_objects.short_description = "Reject selected moderated objects"


def set_objects_as_pending(modeladmin, request, queryset):
    queryset.update(moderation_status=MODERATION_STATUS_PENDING)

set_objects_as_pending.short_description = "Set selected moderated objects "\
                                           "as Pending"


class ModerationAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return list(self.list_display) + ['get_moderation_status']

    def get_moderation_status(self, obj):
        if obj.moderation_active:
            if obj.changeset_set.filter(moderation_status=MODERATION_STATUS_PENDING).exists():
                return _('Pending')
            else:
                return _('Aproved')
        else:
            return _('Created')
    get_moderation_status.short_description = _('Moderation')

    def queryset(self, request):
        return self.model.all_objects.all()

    def get_form(self, request, obj=None):
        return self.get_moderated_object_form(self.model)

    def save_form(self, request, form, change):
        obj = form.save(request=request)
        messages.success(request, _(u"Object is not viewable on site, it will be visible if moderator accepts it"))
        return obj

    def save_model(self, request, obj, form, change):
        return obj

    def get_moderated_object_form(self, model_class):
        class ModeratedObjectForm(BaseModeratedObjectForm):
            class Meta:
                model = model_class
        return ModeratedObjectForm

    def add_view(self, request, *args, **kwargs):
        self.inlines = []
        if "_continue" in request.POST:
            request.POST = request.POST.copy()
            del request.POST["_continue"]

        return super(ModerationAdmin, self).add_view(request, *args, **kwargs)

available_filters = ('content_type', 'moderation_status')

class ModeratedObjectAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_created'
    list_display = ('content_object', 'content_type', 'date_created', 'moderation_status', 'moderated_by', 'moderation_date')
    list_filter = available_filters
    ordering = ['id']
    change_form_template = 'moderation/moderate_object.html'
    change_list_template = 'moderation/moderated_objects_list.html'
    actions = [reject_objects, approve_objects, set_objects_as_pending]
    fieldsets = (
        ('Object moderation', {'fields': ('moderation_reason',)}),
    )

    def get_actions(self, request):
        actions = super(ModeratedObjectAdmin, self).get_actions(request)
        # Remove the delete_selected action if it exists
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def get_moderated_object_form(self, model_class):

        class ModeratedObjectForm(ModelForm):

            class Meta:
                model = model_class

        return ModeratedObjectForm

    def changelist_view(self, request, extra_context=None):
        if not request.GET:
            request.GET = request.GET.copy()
            request.GET.update({'moderation_status__exact': MODERATION_STATUS_PENDING})
        return super(ModeratedObjectAdmin, self).changelist_view(request, extra_context)

    def change_view(self, request, object_id, extra_context=None):
        changeset = Changeset.objects.get(pk=object_id)

        children = changeset.get_children()

        if request.POST:
            admin_form = self.get_form(request, changeset)(request.POST)

            if admin_form.is_valid():
                reason = admin_form.cleaned_data['moderation_reason']
                if 'approve' in request.POST:
                    changeset.approve(request.user, reason)
                elif 'reject' in request.POST:
                    changeset.reject(request.user, reason)

        ct = changeset.content_type
        route = "admin:%s_%s_change" % (ct.app_label, ct.model)
        try:
            object_admin_url = urlresolvers.reverse(route, args=(changeset.object_pk,))
        except urlresolvers.NoReverseMatch:
            object_admin_url = None

        model_klass = ct.model_class()
        full_diff = calculate_full_diff(changeset.content_object or model_klass(), changeset.object_diff)

        children_changes = []
        for c in children:
            children_changes.append({
                'obj': c,
                'diff': calculate_full_diff(c.content_object, c.object_diff)
            })

        extra_context = {'changes': full_diff,
                         'django_version': django.get_version()[:3],
                         'object_admin_url': object_admin_url}
        return super(ModeratedObjectAdmin, self).change_view(request,
            object_id, extra_context=extra_context)


admin.site.register(Changeset, ModeratedObjectAdmin)
