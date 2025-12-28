# from django.contrib import admin
# from .models import ImageHandling, Order, DesignFile, Inventory
# from django.utils.html import format_html
# from .models import MachineDetail
#
# # ===========================
# # IMAGEHANDLING ADMIN
# # ===========================
# @admin.register(ImageHandling)
# class ImageHandlingAdmin(admin.ModelAdmin):
#     list_display = ("title", "image_preview")
#
#     def image_preview(self, obj):
#         if obj.image:
#             return format_html(
#                 '<img src="{}" width="60" height="60" style="object-fit:cover; border-radius:5px;" />'.format(obj.image.url)
#             )
#         return "No Image"
#     image_preview.short_description = "Preview"
#
#
# # ===========================
# # INLINE MODELS
# # ===========================
# class DesignFileInline(admin.TabularInline):
#     model = DesignFile
#     extra = 1
#     fields = ("name", "file", "created_at")
#     readonly_fields = ("created_at",)
#
#
# class InventoryInline(admin.TabularInline):
#     model = Inventory
#     extra = 1
#     fields = ("item_name", "qty", "amount", "status", "created_at")
#     readonly_fields = ("created_at",)
#
#
# # ===========================
# # ORDER ADMIN
# # ===========================
# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#
#     list_display = (
#         "party_name",
#         "stone",
#         "color",
#         "sales_person",
#         "dispatch_status",
#         "current_status",
#         "approval_date",
#         "exp_delivery_date",
#         "image_preview",
#     )
#
#     list_filter = ("dispatch_status", "sales_person", "stone", "color")
#     search_fields = ("party_name", "stone", "sales_person", "color")
#
#     readonly_fields = ("image_preview",)
#
#     inlines = [DesignFileInline, InventoryInline]
#
#     fieldsets = (
#         ("Basic Details", {
#             "fields": (
#                 "title",
#                 "party_name",
#                 "sales_person",
#                 "stone",
#                 "color",
#                 "remarks",
#             )
#         }),
#         ("Images", {
#             "fields": ("image", "image_preview")
#         }),
#         ("Dates", {
#             "fields": ("approval_date", "exp_delivery_date")
#         }),
#         ("Additional Info", {
#             "fields": ("coverage_area", "packing_instruction", "dispatch_status")
#         }),
#     )
#
#     def image_preview(self, obj):
#         if obj.image:
#             return format_html(
#                 '<img src="{}" width="80" style="border-radius:4px;" />'.format(obj.image.url)
#             )
#         return "No Image"
#     image_preview.short_description = "Image Preview"
#
#
# # ===========================
# # DESIGN FILE ADMIN
# # ===========================
# @admin.register(DesignFile)
# class DesignFileAdmin(admin.ModelAdmin):
#     list_display = ("order", "name", "file", "created_at")
#     search_fields = ("name", "order__party_name", "order__stone")
#     list_filter = ("created_at",)
#
#
# # ===========================
# # INVENTORY ADMIN
# # ===========================
# @admin.register(Inventory)
# class InventoryAdmin(admin.ModelAdmin):
#     list_display = ("order", "item_name", "qty", "amount", "status", "created_at")
#     list_filter = ("status", "created_at")
#     search_fields = ("item_name", "order__party_name", "order__stone")
#
#
# @admin.register(MachineDetail)
# class MachineDetailAdmin(admin.ModelAdmin):
#     list_display = ("machine_name", "working_hour", "operator","remarks", "created_at")
