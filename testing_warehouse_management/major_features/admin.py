from django.contrib import admin
from . models import *

# Register your models here.
admin.site.register(WarehouseManagementMethod)
admin.site.register(AccoutingPeriod)
admin.site.register(AccountingPeriodInventory)
admin.site.register(Product)
admin.site.register(Supplier)
admin.site.register(Agency)
admin.site.register(ImportShipment)
admin.site.register(ImportPurchase)
admin.site.register(ExportShipment)
admin.site.register(ExportOrder)
admin.site.register(ExportOrderDetail)
admin.site.register(UserActivity)
admin.site.register(Category)
