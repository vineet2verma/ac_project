from django.db import models
from cloudinary.models import CloudinaryField
# Create your models here.


class ImageHandling(models.Model):
    title = models.CharField(max_length=100)
    image = CloudinaryField('image', blank=True, null=True)

    def __str__(self):
        return self.title

# Sales Orders
class Order(models.Model):
    cnc_order_no = models.CharField(max_length=100, unique=True, blank=True, null=True)
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to="orders/", blank=True, null=True)
    stone = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=200)
    remarks = models.TextField(blank=True, null=True)
    packing_instruction = models.TextField(blank=True, null=True)
    approval_date = models.DateField(blank=True, null=True)
    exp_delivery_date = models.DateField(blank=True, null=True)
    coverage_area = models.CharField(max_length=50)
    party_name = models.CharField(max_length=200)
    sales_person = models.CharField(max_length=100)
    dispatch_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("complete", "Complete")],
        default="pending"
    )

# Design
class DesignFile(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("cancelled", "Cancelled"),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    file = CloudinaryField('design_file', resource_type='auto', folder='design_files')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Inventory
class Inventory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=200)
    qty = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("complete", "Complete")],
        default="pending"
    )

    @property
    def total(self):
        return self.qty * self.amount

# Machine Master
class MachineMaster(models.Model):
    machine_no = models.CharField(max_length=50, unique=True, blank=True, null=True)
    machine_name = models.CharField(max_length=150, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.machine_name} - {self.machine_no}"

# Machine Detail
class MachineDetail(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="machine_details")
    machine_name = models.ForeignKey(MachineMaster, on_delete=models.CASCADE, blank=True, null=True,
                                     related_name="machine_details")
    working_hour = models.DecimalField(max_digits=6, decimal_places=2)
    operator = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.machine_name}"

# QC
class QualityCheck(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    checked_by = models.CharField(max_length=100)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pass", "Pass"),
            ("fail", "Fail"),
        ],
        default="pass"
    )
    checked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"QC - {self.order.id}"

# Dispatch
class Dispatch(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    vehicle_no = models.CharField(max_length=50)
    lr_no = models.CharField(max_length=50)
    dispatch_date = models.DateField()
    dispatched_by = models.CharField(max_length=100)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Dispatch - {self.order.id}"



# ###########################################
# class Order(models.Model):
#     cnc_order_no = models.CharField(max_length=50, unique=True,blank=True, null=True)
#     title = models.CharField(max_length=100)
#     image = CloudinaryField('order_image', folder='orders', blank=True, null=True)
#     stone = models.CharField(max_length=100)
#     color = models.CharField(max_length=200)
#     remarks = models.TextField(blank=True, null=True)
#     packing_instruction = models.TextField(blank=True, null=True)
#     approval_date = models.DateField()
#     exp_delivery_date = models.DateField()
#     coverage_area = models.CharField(max_length=50)
#     party_name = models.CharField(max_length=200)
#     sales_person = models.CharField(max_length=100)
#     dispatch_status = models.CharField(
#         max_length=20,
#         choices=[("pending", "Pending"), ("complete", "Complete")],
#         default="pending"
#     )
#
#     @property
#     def current_status(self):
#         if not self.designfile_set.exists():
#             return "Design Working"
#
#         if self.inventory_set.filter(status="complete").count() < self.inventory_set.count():
#             return "Inventory Pending"
#
#         if self.dispatch_status != "complete":
#             return "Dispatch Pending"
#
#         return "Complete"
#
#
#     def __str__(self):
#         return f"{self.party_name} - {self.stone}"
#
